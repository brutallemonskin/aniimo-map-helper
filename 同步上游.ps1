param([switch]$CheckOnly)

$ErrorActionPreference = 'Stop'
$repoRoot = $PSScriptRoot

function Invoke-RepositoryGit {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    $result = & git -C $repoRoot @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Git 操作失败：$($Arguments -join ' ')" }
    return $result
}

try {
    $branch = Invoke-RepositoryGit branch --show-current
    if ($branch -ne 'codex/gpu-recognition') {
        throw '请先切换到 codex/gpu-recognition 本地优化分支。'
    }
    if (Invoke-RepositoryGit status --porcelain) {
        throw '工作区有未提交内容，请先提交或自行保存，再同步上游。'
    }
    Invoke-RepositoryGit fetch origin main
    & git -C $repoRoot merge-base --is-ancestor origin/main HEAD
    $ancestryResult = $LASTEXITCODE
    if ($ancestryResult -eq 0) {
        Write-Output '当前分支已包含上游最新更新，本地优化保持完整。'
        exit 0
    }
    if ($ancestryResult -ne 1) { throw '无法检查上游提交关系。' }
    Invoke-RepositoryGit log --oneline HEAD..origin/main
    if ($CheckOnly) { Write-Output '以上为尚未合并的上游提交；此次只检查。'; exit 0 }
    $backupBranch = 'codex/backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
    Invoke-RepositoryGit branch $backupBranch
    Write-Output "已建立同步前备份分支：$backupBranch"
    & git -C $repoRoot merge --no-ff origin/main -m 'chore(upstream): 合并 GitHub 上游更新并保留本地优化'
    if ($LASTEXITCODE -ne 0) {
        Write-Output '合并尚未完成。请检查 git status，解决冲突后提交；放弃本次合并可执行 git merge --abort。'
        exit 1
    }
    Write-Output '已合并上游。请按“本地优化说明.md”运行回归检查，再重新构建便携版。'
} catch {
    Write-Error $_
    exit 1
}
