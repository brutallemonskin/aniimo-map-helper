"""每次构建使用独立的资源地址，避免浏览器混用新后端与旧脚本。"""
import json
import re
from urllib.parse import quote


def versioned_html(source,version):
    def asset(match):
        url=match.group(2)
        separator='&' if '?' in url else '?'
        return match.group(1)+url+separator+'local='+quote(version,safe='')+'"'
    source=re.sub(r'((?:src|href)=")([^"\s]+\.(?:js|css)(?:\?[^"\s]*)?)"',asset,source)
    build='<script>window.ANIIMO_BUILD='+json.dumps(version)+';</script>'
    return source.replace('</head>',build+'</head>',1)
