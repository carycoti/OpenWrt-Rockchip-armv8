#!/bin/bash
# =================================================================
# Copyright (c) 2019-2020 P3TERX <https://p3terx.com>
#
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#
# https://github.com/P3TERX/Actions-OpenWrt
# File name: diy-part1.sh
# Description: OpenWrt DIY script part 1 (Before Update feeds)
# =================================================================

# 执行命令来切换内核
#sed -i 's/PATCHVER:=6.1/PATCHVER:=6.6/g' target/linux/rockchip/Makefile

shopt -s extglob
# 添加软件源
sed -i '$a src-git kiddin9 https://github.com/kiddin9/kwrt-packages.git;main' feeds.conf.default

# 添加 kenzok8源
# sed -i '1i src-git kenzo https://github.com/kenzok8/openwrt-packages' feeds.conf.default
# sed -i '2i src-git small https://github.com/kenzok8/small' feeds.conf.default
# sed -i '$a src-git smpackage https://github.com/kenzok8/small-package' feeds.conf.default

# 删除 telephony feeds,并优化feeds命令
sed -i "/telephony/d" feeds.conf.default
sed -i "s?targets/%S/packages?targets/%S/\$(LINUX_VERSION)?" include/feeds.mk
sed -i '/	refresh_config();/d' scripts/feeds

# 更新 feeds
./scripts/feeds update -a

# 修改 Makefile
find package/*/ -maxdepth 2 -path "*/Makefile" | xargs -i sed -i 's/..\/..\/luci.mk/$(TOPDIR)\/feeds\/luci\/luci.mk/g' {}
find package/*/ -maxdepth 2 -path "*/Makefile" | xargs -i sed -i 's/..\/..\/lang\/golang\/golang-package.mk/$(TOPDIR)\/feeds\/packages\/lang\/golang\/golang-package.mk/g' {}
find package/*/ -maxdepth 2 -path "*/Makefile" | xargs -i sed -i 's/PKG_SOURCE_URL:=@GHREPO/PKG_SOURCE_URL:=https:\/\/github.com/g' {}
find package/*/ -maxdepth 2 -path "*/Makefile" | xargs -i sed -i 's/PKG_SOURCE_URL:=@GHCODELOAD/PKG_SOURCE_URL:=https:\/\/codeload.github.com/g' {}

# 取消对 samba4 的菜单调整
# sed -i '/samba4/s/^/#/' package/lean/default-settings/files/zzz-default-settings

# Themes
# rm -rf feeds/luci/themes/luci-theme-argon
# rm -rf feeds/luci/themes/luci-theme-bootstrap-mmdvm
# git clone https://github.com/jerrykuku/luci-theme-argon.git package/luci-theme-argon

# 为 kenzok8 源整理相关目录
# rm -rf feeds/luci/applications/luci-app-mosdns
# rm -rf feeds/packages/net/{alist,adguardhome,mosdns,xray*,v2ray*,v2ray*,sing*,smartdns}
# rm -rf feeds/packages/utils/v2dat
# rm -rf feeds/smpackage/{base-files,dnsmasq,firewall*,fullconenat,libnftnl,nftables,ppp,opkg,ucl,upx,vsftpd*,miniupnpd-iptables,wireless-regdb}

# 替换 golang
rm -rf feeds/packages/lang/golang
git clone https://github.com/kenzok8/golang feeds/packages/lang/golang

# 替换编译出错的包
rm -rf feeds/packages/lang/ruby
git clone https://github.com/coolsnowwolf/packages tmp/lede-packages
mv tmp/lede-packages/lang/ruby feeds/packages/lang/ruby
# mv tmp/lede-packages/net/gowebdav feeds/packages/net/gowebdav
# mv tmp/lede-packages/utils/bandwidthd feeds/packages/utils/bandwidthd
# mv tmp/lede-packages/net/shadowsocks-libev feeds/packages/net/shadowsocks-libev
# mv tmp/lede-packages/libs/pcre2 feeds/packages/libs/pcre2
# rm -rf tmp/lede-packages

# 2024-07-24临时更改chinadns-ng
sed -i "s/PKG_MIRROR_HASH:=ed7c71afb74c8232cfda084545ad8c1f8fe6c5e8176da9a77729e1fa9044d863/PKG_MIRROR_HASH:=skip/" feeds/packages/net/trojan-plus/Makefile
sed -i 's/PKG_MIRROR_HASH:=.*/PKG_MIRROR_HASH:=skip/' feeds/kiddin9/trojan-plus/Makefile
sed -i "s/PKG_MIRROR_HASH:=0981bf49cb8a6e7f81912808987727bf6a2454ad0a3cf744f1a64bfc1969b088/PKG_MIRROR_HASH:=skip/" feeds/packages/net/redsocks2/Makefile

sed -i "s/PKG_MIRROR_HASH:=0981bf49cb8a6e7f81912808987727bf6a2454ad0a3cf744f1a64bfc1969b088/PKG_MIRROR_HASH:=skip/" feeds/small/redsocks2/Makefile

sed -i "s/PKG_MIRROR_HASH:=e70dd8843c3688b58f66fff5320a93d5789b79114bcb36a94d5b554664439f04/PKG_MIRROR_HASH:=skip/" feeds/packages/lang/lua-maxminddb/Makefile

sed -i "s/PKG_MIRROR_HASH:=e70dd8843c3688b58f66fff5320a93d5789b79114bcb36a94d5b554664439f04/PKG_MIRROR_HASH:=skip/" feeds/kenzo/lua-maxminddb/Makefile

# kiddin9 相关的冲突包
rm -rf feeds/packages/net/{alist,mosdns,xray*,v2ray*,v2ray*,smartdns}
rm -rf feeds/packages/utils/v2dat
rm -rf feeds/kiddin9/{base-files,dnsmasq,firewall*,fullconenat,libnftnl,nftables,ppp,opkg,upx,miniupnpd-iptables,wireless-regdb,quectel_SRPD_PCIE,adguardhome,shortcut-fe,fibocom_QMI_WWAN,quectel_QMI_WWAN,rtl8189es,quectel_Gobinet,quectel_MHI,accel-ppp,dockerd,cgroupfs-mount,lua-maxminddb,luci-app-linkease,luci-app-quickstart,fullconenat-nft,redsocks2,shadowsocks-libev,shadowsocksr-libev}
mv -f feeds/kiddin9/r81* tmp/

# 替换 quickstart.lua
curl -sL https://raw.githubusercontent.com/kenzok8/openwrt-packages/master/luci-app-quickstart/luasrc/controller/quickstart.lua -o feeds/kiddin9/luci-app-quickstart/luasrc/controller/quickstart.lua

./scripts/feeds install -a -p kiddin9 -f

# 安装 feeds
./scripts/feeds install -a
