param(
    [string]$ReportPath = (Join-Path $PSScriptRoot '..\docs\report\Bao_cao_blockchain_da_chinh_sua.docx')
)
$ErrorActionPreference = 'Stop'
$resolvedReport = (Resolve-Path -LiteralPath $ReportPath).Path
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if (-not $resolvedReport.StartsWith($workspaceRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Only render the edited report within this workspace.'
}
$pdfPath = [IO.Path]::ChangeExtension($resolvedReport, '.pdf')
$word = $null
$document = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    # Disable macros before opening any document.
    $word.AutomationSecurity = 3
    $document = $word.Documents.Open($resolvedReport, $false, $false, $false)
    $document.Fields.Update() | Out-Null
    for ($index = 1; $index -le $document.TablesOfContents.Count; $index++) {
        $document.TablesOfContents.Item($index).Update()
    }
    $document.Repaginate()
    $document.Save()
    $document.ExportAsFixedFormat($pdfPath, 17)
    [PSCustomObject]@{
        Docx = $resolvedReport
        Pdf = $pdfPath
        Pages = $document.ComputeStatistics(2)
        TablesOfContents = $document.TablesOfContents.Count
    } | ConvertTo-Json
} finally {
    if ($null -ne $document) {
        $document.Close(0)
        [Runtime.InteropServices.Marshal]::FinalReleaseComObject($document) | Out-Null
    }
    if ($null -ne $word) {
        $word.Quit()
        [Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) | Out-Null
    }
}
