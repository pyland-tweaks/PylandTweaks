# PylandTweaks - Planes de energia (seguros y reversibles)
$ErrorActionPreference = 'SilentlyContinue'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path

$PlanBalanced = '381b4222-f694-41f0-9685-ff5bb260df2e'
$PlanHigh     = '8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c'
$PlanUltimate = 'e9a42b02-d5df-448d-aa00-03f14749eb61'

function Get-ActivePlanText { (powercfg /getactivescheme) -join ' ' }

function Save-PrevPlan {
    $m = [regex]::Match((Get-ActivePlanText), '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')
    if ($m.Success) {
        Set-Content -LiteralPath (Join-Path $Here 'prev_plan.txt') -Value $m.Value -Encoding ASCII
    }
}

function Ensure-DuplicatedPlan([string]$Source, [string]$Tag) {
    $file = Join-Path $Here "plan_${Tag}_guid.txt"
    if (Test-Path -LiteralPath $file) {
        $g = (Get-Content -LiteralPath $file -Raw).Trim()
        if ($g -and ((powercfg /list) -join ' ') -match [regex]::Escape($g)) { return $g }
    }
    $out = (powercfg -duplicatescheme $Source) -join ' '
    $m = [regex]::Match($out, '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')
    if (-not $m.Success) { return '' }
    Set-Content -LiteralPath $file -Value $m.Value -Encoding ASCII
    return $m.Value
}

function Tune-GamingPlan([string]$G) {
    $items = @(
        @('SUB_PROCESSOR', 'PROCTHROTTLEMIN', '100'),
        @('SUB_PROCESSOR', 'PROCTHROTTLEMAX', '100'),
        @('SUB_PROCESSOR', 'CPMINCORES', '100'),
        @('SUB_PROCESSOR', 'CPMAXCORES', '100'),
        @('SUB_PROCESSOR', 'PERFBOOSTMODE', '2'),
        @('SUB_PROCESSOR', 'IDLEDISABLE', '1'),
        @('SUB_PROCESSOR', 'SYSCOOLPOL', '1'),
        @('SUB_PCIEXPRESS', 'ASPM', '0'),
        @('SUB_DISK', 'DISKIDLE', '0'),
        @('SUB_USB', 'USBSELECTIVESUSPEND', '0')
    )
    foreach ($it in $items) {
        powercfg -setacvalueindex $G $it[0] $it[1] $it[2] | Out-Null
    }
    powercfg -setactive $G | Out-Null
}

function Apply-Plan([string]$Kind) {
    Save-PrevPlan
    switch ($Kind) {
        'balanced' { powercfg -setactive $PlanBalanced | Out-Null }
        'high'     { powercfg -setactive $PlanHigh | Out-Null }
        'ultimate' {
            $g = Ensure-DuplicatedPlan $PlanUltimate 'ultimate'
            if (-not $g) { Write-Host 'No se pudo crear el plan Ultimate.' -ForegroundColor Red; return }
            powercfg -setactive $g | Out-Null
        }
        'gaming' {
            $g = Ensure-DuplicatedPlan $PlanHigh 'gaming'
            if (-not $g) { Write-Host 'No se pudo crear el plan Pyland Gaming.' -ForegroundColor Red; return }
            Tune-GamingPlan $g
        }
        'prev' {
            $file = Join-Path $Here 'prev_plan.txt'
            $g = ''
            if (Test-Path -LiteralPath $file) { $g = (Get-Content -LiteralPath $file -Raw).Trim() }
            if (-not $g) { $g = $PlanBalanced }
            powercfg -setactive $g | Out-Null
        }
    }
    Write-Host ''
    Write-Host 'Plan activo ahora:' -ForegroundColor Green
    Get-ActivePlanText
}

while ($true) {
    Clear-Host
    Write-Host '==================================================' -ForegroundColor Cyan
    Write-Host '        PylandTweaks - Planes de energia' -ForegroundColor Cyan
    Write-Host '==================================================' -ForegroundColor Cyan
    Write-Host ''
    Write-Host '  1. Equilibrado (Windows)'
    Write-Host '  2. Alto rendimiento'
    Write-Host '  3. Maximo rendimiento (Ultimate)'
    Write-Host '  4. Pyland Gaming (baja latencia)  [recomendado]'
    Write-Host '  5. Restaurar plan anterior'
    Write-Host '  6. Ver plan actual'
    Write-Host '  0. Salir'
    Write-Host ''
    $op = Read-Host 'Opcion'
    switch ($op) {
        '1' { Apply-Plan 'balanced' }
        '2' { Apply-Plan 'high' }
        '3' { Apply-Plan 'ultimate' }
        '4' { Apply-Plan 'gaming' }
        '5' { Apply-Plan 'prev' }
        '6' { Write-Host ''; Get-ActivePlanText }
        '0' { return }
        default { Write-Host 'Opcion no valida.' -ForegroundColor Yellow }
    }
    Write-Host ''
    Read-Host 'Pulsa ENTER para continuar'
}
