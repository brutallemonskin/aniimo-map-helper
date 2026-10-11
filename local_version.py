"""本地优化修订独立于上游版本，合并更新时保留两者的来源。"""
LOCAL_VERSION = '0.0.6'


def local_version(upstream):
    return upstream + '+local.' + LOCAL_VERSION
