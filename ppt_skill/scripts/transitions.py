#!/usr/bin/env python3
"""Give a .pptx real PowerPoint slide transitions.

python-pptx has no transition API at all, so this rewrites the slide parts of
an existing package. The result is a genuine `<p:transition>` element - the
same thing PowerPoint writes when you pick a transition in the ribbon - so the
effect actually plays, rather than being a note that says "Fade".

    python transitions.py deck.pptx --config transitions.json
    python transitions.py deck.pptx --preset fade --duration 700

Config JSON, either a default with per-slide overrides:

    {"default": {"type": "fade", "duration": 700},
     "slides": {"3": {"type": "push", "dir": "l", "duration": 700}}}

or a list in display order (entry 0 is the first slide, which is never
transitioned *into*, so it is usually null):

    {"transitions": [null, {"type": "fade", "duration": 800}]}

Supported types: fade, dissolve, cut, push, wipe, cover, split.
Durations are milliseconds. A null spec removes that slide's transition.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import zipfile

from lxml import etree

XMLNS = "http://www.w3.org/2000/xmlns/"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_P14 = "http://schemas.microsoft.com/office/powerpoint/2010/main"
NS_MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PR = "http://schemas.openxmlformats.org/package/2006/relationships"

XML_DECL = b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'

# Registering the prefixes makes lxml emit them by name when it has to declare
# these namespaces, instead of inventing ns0/ns1 placeholders.
etree.register_namespace("mc", NS_MC)
etree.register_namespace("p14", NS_P14)

DIRECTED = {"push", "wipe", "cover"}
SIMPLE = {"fade", "dissolve", "cut"}


def qn(tag):
    prefix, local = tag.split(":")
    uri = {"p": NS_P, "p14": NS_P14, "mc": NS_MC, "r": NS_R}.get(prefix)
    return "{%s}%s" % (uri, local)


def _child_xml(ttype, direction):
    ns = 'xmlns:p="%s"' % NS_P
    if ttype in SIMPLE:
        return "<p:%s %s/>" % (ttype, ns)
    if ttype in DIRECTED:
        return '<p:%s %s dir="%s"/>' % (ttype, ns, direction or "l")
    if ttype == "split":
        orient = "horz" if (direction or "l") in ("l", "r") else "vert"
        return '<p:split %s orient="%s" dir="out"/>' % (ns, orient)
    raise ValueError("unsupported transition type %r (supported: %s)"
                     % (ttype, ", ".join(sorted(SIMPLE | DIRECTED | {"split"}))))


def _speed(duration_ms):
    """Legacy `spd` attribute, so older readers still get a sensible speed."""
    if duration_ms is None:
        return None
    return "slow" if duration_ms >= 1000 else ("fast" if duration_ms < 500 else "med")


def build_transition(spec):
    """Return a <p:transition> element for a config entry."""
    ttype = spec.get("type", "fade")
    duration = spec.get("duration")
    attrs = []
    if spec.get("adv_click", True) is False:
        attrs.append('advClick="0"')
    if spec.get("adv_tm"):
        attrs.append('advTm="%d"' % int(spec["advTm"]))
    speed = _speed(duration)
    if speed:
        attrs.append('spd="%s"' % speed)
    dur_attr = ""
    if duration:
        dur_attr = ' p14:dur="%d"' % int(duration)
    xml = ('<p:transition xmlns:p="%s" xmlns:p14="%s" %s%s>%s</p:transition>'
           % (NS_P, NS_P14, " ".join(attrs), dur_attr,
              _child_xml(ttype, spec.get("dir"))))
    return etree.fromstring(xml.encode("utf-8"))


def _insert_in_schema_order(sld, element):
    """CT_Slide order is cSld, clrMapOvr, transition, timing, extLst."""
    for tag in ("p:timing", "p:extLst"):
        ref = sld.find(qn(tag))
        if ref is not None:
            ref.addprevious(element)
            return
    sld.append(element)


def _serialize(root):
    out = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    # lxml writes single-quoted declarations; normalise to the OOXML convention
    if out.startswith(b"<?xml version='1.0'"):
        out = XML_DECL + out.split(b"?>", 1)[1].lstrip(b"\r\n")
    return out + b"\n"


def apply_to_slide(slide_bytes, spec):
    """Add (or remove, when spec is None) the transition on one slide part.

    Note on the namespace handling: the p14 extension namespace must be marked
    ignorable for pre-2010 readers. Setting the attribute *in* the mc namespace
    lets lxml declare xmlns:mc itself. Hand-writing the xmlns declaration via
    lxml's xmlns-namespace attribute trick instead corrupts the part with
    "reuse of the xmlns namespace name is forbidden".
    """
    if slide_bytes.startswith(b"\xef\xbb\xbf"):
        slide_bytes = slide_bytes[3:]
    root = etree.fromstring(slide_bytes)
    for old in root.findall(qn("p:transition")):
        root.remove(old)
    if spec is None:
        return _serialize(root)
    ignorable = (root.get(qn("mc:Ignorable")) or "").split()
    if "p14" not in ignorable:
        ignorable.append("p14")
    root.set(qn("mc:Ignorable"), " ".join(ignorable))
    _insert_in_schema_order(root, build_transition(spec))
    return _serialize(root)


def slide_parts_in_order(zf):
    """Resolve slide parts through the presentation rels, not filename order."""
    names = set(zf.namelist())
    pres = etree.fromstring(zf.read("ppt/presentation.xml"))
    rels = etree.fromstring(zf.read("ppt/_rels/presentation.xml.rels"))
    target = {rel.get("Id"): rel.get("Target") for rel in rels}
    parts = []
    for sld_id in pres.iter(qn("p:sldId")):
        rid = sld_id.get(qn("r:id"))
        tgt = target.get(rid)
        if not tgt:
            continue
        tgt = tgt[1:] if tgt.startswith("/") else "ppt/" + tgt.lstrip("./")
        if tgt.replace("\\", "/") in names:
            parts.append(tgt.replace("\\", "/"))
    return parts


def resolve_config(config, count):
    """Expand a config file into one entry per slide (index 0 = slide 1)."""
    if config is None:
        return [None] * count
    if "transitions" in config:
        items = list(config["transitions"])
        items += [None] * (count - len(items))
        return items[:count]
    default = config.get("default")
    overrides = config.get("slides", {})
    out = []
    for i in range(count):
        spec = overrides.get(str(i + 1), default)
        out.append(spec)
    return out


def add_transitions(path, config, out_path=None):
    out_path = out_path or path
    tmp = str(out_path) + ".tmp"
    with zipfile.ZipFile(path) as zin:
        parts = slide_parts_in_order(zin)
        specs = resolve_config(config, len(parts))
        replaced = {}
        for part, spec in zip(parts, specs):
            replaced[part] = apply_to_slide(zin.read(part), spec)
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = replaced.get(item.filename, zin.read(item.filename))
                zout.writestr(item, data)
    shutil.move(tmp, out_path)
    applied = sum(1 for s in specs if s)
    return {"slides": len(parts), "transitions": applied,
            "types": sorted({s.get("type", "fade") for s in specs if s})}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Add real slide transitions to a .pptx.")
    ap.add_argument("deck")
    ap.add_argument("--config", help="transition config JSON")
    ap.add_argument("--preset", default="fade",
                    choices=sorted(SIMPLE | DIRECTED | {"split"}),
                    help="transition type when no config is given")
    ap.add_argument("--duration", type=int, default=700)
    ap.add_argument("-o", "--out", help="output path (defaults to in-place)")
    args = ap.parse_args(argv)

    if args.config:
        with open(args.config, encoding="utf-8") as fh:
            config = json.load(fh)
    else:
        config = {"default": {"type": args.preset, "duration": args.duration}}
    try:
        summary = add_transitions(args.deck, config, args.out)
    except (ValueError, KeyError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print("transitions: %d applied across %d slides (%s)"
          % (summary["transitions"], summary["slides"], ", ".join(summary["types"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
