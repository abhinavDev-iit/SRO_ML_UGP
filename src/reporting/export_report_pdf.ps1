param(
    [string]$DocxPath = "deliverables/SRO_ML_Project_Progress_Report.docx",
    [string]$PdfPath = "deliverables/SRO_ML_Project_Progress_Report.pdf"
)

$ErrorActionPreference = "Stop"
$docx = (Resolve-Path -LiteralPath $DocxPath).Path
$pdf = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $PdfPath))
$word = $null
$document = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $document = $word.Documents.Open($docx)
    $document.Repaginate()
    foreach ($toc in $document.TablesOfContents) { $toc.Update() }
    foreach ($styleName in @("toc 1", "toc 2")) {
        $style = $document.Styles.Item($styleName)
        $style.Font.Name = "Calibri"
        $style.Font.Size = 8.5
        $style.ParagraphFormat.SpaceBefore = 0
        $style.ParagraphFormat.SpaceAfter = 0
        $style.ParagraphFormat.LineSpacingRule = 0
    }
    $document.Fields.Update() | Out-Null
    $document.Repaginate()
    foreach ($toc in $document.TablesOfContents) { $toc.UpdatePageNumbers() }
    $document.Save()
    # 17 = wdExportFormatPDF; 0 = print document; 0 = optimize for print.
    $document.ExportAsFixedFormat($pdf, 17, $false, 0, 0)
    Write-Output $pdf
}
finally {
    if ($document -ne $null) { $document.Close($false) }
    if ($word -ne $null) { $word.Quit() }
    if ($document -ne $null) { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($document) | Out-Null }
    if ($word -ne $null) { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
