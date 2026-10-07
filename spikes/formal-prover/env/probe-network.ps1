# Checks that track D's tool sources are reachable through the proxy (mise task check:formal-network).
# Uses curl.exe (Schannel, OS trust store) rather than Invoke-WebRequest, which timed out on
# large files during the general toolchain-feasibility spike. A body containing the proxy's
# block notice counts as blocked. Narrowed from that spike's wider probe to what track D's image
# and native routes actually use.
param([int] $TimeoutSec = 60)

$targets = [ordered]@{
    'opam releases (GitHub API)'  = 'https://api.github.com/repos/ocaml/opam/releases/latest'
    'Rocq opam repository'        = 'https://rocq-prover.org/opam/released/repo'
    'Isabelle Cambridge mirror'   = 'https://www.cl.cam.ac.uk/research/hvg/Isabelle/dist/'
    'Docker Hub registry'         = 'https://registry-1.docker.io/v2/'
}

foreach ($name in $targets.Keys) {
    $url = $targets[$name]
    $tmp = New-TemporaryFile
    $meta = curl.exe -sS -L -o $tmp.FullName --max-time $TimeoutSec -r 0-65535 -w '%{http_code} %{url_effective}' $url 2>&1
    $body = Get-Content $tmp.FullName -Raw -ErrorAction SilentlyContinue
    Remove-Item $tmp.FullName -ErrorAction SilentlyContinue
    # The proxy redirects a blocked request to its notice page, whose URL names the block reason.
    $blocked = ($body -match 'Block Notice|Not allowed to browse') -or ($meta -match 'Block\+Notice|cgi-bin/notice')
    $code = ($meta -split ' ')[0]
    # 401 from a container registry is the normal anonymous challenge, so it counts as reachable.
    $status = if ($blocked) { 'BLOCKED' } elseif ($code -match '^(2|3)\d\d$|^401$') { 'ok' } else { "FAIL ($meta)" }
    '{0,-30} {1,-8} {2}' -f $name, $status, $url
}
