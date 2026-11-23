"""Save an authorized direct HTTPS PDF with a local provenance record."""

from hashlib import sha256
from pathlib import Path
from shutil import copyfileobj
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener


def check_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("请提供无用户名和密码的 HTTPS 全文链接")


class HTTPSRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_pdf(url, target):
    check_url(url)
    if target.suffix.lower() != ".pdf":
        raise ValueError("PDF 输出路径须使用 .pdf 后缀")
    if target.exists():
        raise FileExistsError(f"PDF 已存在：{target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = sha256()
    size = 0
    with TemporaryDirectory(dir=target.parent) as folder:
        staged = Path(folder) / "download.pdf"
        opener = build_opener(HTTPSRedirect())
        with opener.open(url, timeout=30) as response, staged.open("wb") as file:
            final_url = response.geturl()
            check_url(final_url)
            header = response.read(8)
            if not header.startswith(b"%PDF-"):
                raise ValueError("来源没有返回 PDF，请核查链接或访问权限")
            while header:
                file.write(header)
                digest.update(header)
                size += len(header)
                header = response.read(64 * 1024)
        with staged.open("rb") as file:
            file.seek(max(0, size - 1024))
            if b"%%EOF" not in file.read():
                raise ValueError("PDF 缺少文件尾标记，请重新获取")
            file.seek(0)
            output = target.open("xb")
            try:
                with output:
                    copyfileobj(file, output)
            except OSError:
                target.unlink()
                raise
    return {"path": str(target), "url": final_url, "bytes": size, "sha256": digest.hexdigest()}
