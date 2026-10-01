param(
    [Parameter(Mandatory=$true)][string]$Pdf,
    [Parameter(Mandatory=$true)][string]$OutputPrefix
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime] | Out-Null
[Windows.Data.Pdf.PdfDocument, Windows.Data.Pdf, ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime] | Out-Null
[Windows.Data.Pdf.PdfPageRenderOptions, Windows.Data.Pdf, ContentType=WindowsRuntime] | Out-Null
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]
function Await-Result($operation, $type) {
    $task = $asTask.MakeGenericMethod($type).Invoke($null, @($operation))
    $task.Wait()
    $task.Result
}
$asAction = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and -not $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction'
})[0]
$file = Await-Result ([Windows.Storage.StorageFile]::GetFileFromPathAsync([IO.Path]::GetFullPath($Pdf))) ([Windows.Storage.StorageFile])
$document = Await-Result ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($file)) ([Windows.Data.Pdf.PdfDocument])
for ($i = 0; $i -lt $document.PageCount; $i++) {
    $page = $document.GetPage($i)
    $memory = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
    $options = New-Object Windows.Data.Pdf.PdfPageRenderOptions
    $options.DestinationWidth = 1200
    try {
        $task = $asAction.Invoke($null, @($page.RenderToStreamAsync($memory, $options)))
        $task.Wait()
        $stream = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($memory)
        $output = [IO.File]::Create([IO.Path]::GetFullPath(('{0}-{1:D2}.png' -f $OutputPrefix, ($i + 1))))
        try { $stream.CopyTo($output) } finally { $output.Dispose(); $stream.Dispose() }
    } finally { $page.Dispose(); $memory.Dispose() }
}
Write-Output "Rendered $($document.PageCount) PDF pages to PNG."
