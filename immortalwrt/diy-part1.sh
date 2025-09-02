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
# sed -i '$a src-git kiddin9 https://github.com/kiddin9/openwrt-packages.git;master' feeds.conf.default

# kenzok8
# sed -i '1i src-git kenzo https://github.com/kenzok8/openwrt-packages' feeds.conf.default
# sed -i '2i src-git small https://github.com/kenzok8/small' feeds.conf.default
# sed -i '$a src-git smpackage https://github.com/kenzok8/small-package' feeds.conf.default

# istore
# echo 'src-git nas https://github.com/linkease/nas-packages.git;master' >> feeds.conf.default
# echo 'src-git nas_luci https://github.com/linkease/nas-packages-luci.git;main' >> feeds.conf.default
 
sed -i "/telephony/d" feeds.conf.default
sed -i "s?targets/%S/packages?targets/%S/\$(LINUX_VERSION)?" include/feeds.mk
sed -i '/	refresh_config();/d' scripts/feeds

# 修改 Makefile
find package/*/ -maxdepth 2 -path "*/Makefile" | xargs -i sed -i 's/..\/..\/luci.mk/$(TOPDIR)\/feeds\/luci\/luci.mk/g' {}
# find package/*/ -maxdepth 2 -path "*/Makefile" | xargs -i sed -i 's/..\/..\/lang\/golang\/golang-package.mk/$(TOPDIR)\/feeds\/packages\/lang\/golang\/golang-package.mk/g' {}
find package/*/ -maxdepth 2 -path "*/Makefile" | xargs -i sed -i 's/PKG_SOURCE_URL:=@GHREPO/PKG_SOURCE_URL:=https:\/\/github.com/g' {}
find package/*/ -maxdepth 2 -path "*/Makefile" | xargs -i sed -i 's/PKG_SOURCE_URL:=@GHCODELOAD/PKG_SOURCE_URL:=https:\/\/codeload.github.com/g' {}

# 取消对 samba4 的菜单调整
# sed -i '/samba4/s/^/#/' package/lean/default-settings/files/zzz-default-settings

./scripts/feeds update -a
# ./scripts/feeds install -a -p kiddin9 -f

# 替换中文,解决中文包无效的问题
# sed -i "s/option lang auto/option lang zh_cn/" feeds/luci/modules/luci-base/root/etc/config/luci
# sed -i "/config internal languages/a\\\toption zh_cn 'chinese'\n\toption en 'English'" feeds/luci/modules/luci-base/root/etc/config/luci

# Themes
# rm -rf feeds/luci/themes/luci-theme-argon
#rm -rf feeds/luci/themes/luci-theme-bootstrap-mmdvm
# git clone https://github.com/jerrykuku/luci-theme-argon.git package/luci-theme-argon

# kenzok8
# rm -rf feeds/kenzo/luci-theme-argon
# rm -rf feeds/kenzo/luci-app-istorex
# rm -rf feeds/kenzo/luci-app-quickstart
# rm -rf feeds/kenzo/quickstart
# rm -rf feeds/luci/applications/luci-app-mosdns
# rm -rf feeds/packages/net/{alist,adguardhome,mosdns,xray*,v2ray*,v2ray*,sing*,smartdns}
# rm -rf feeds/packages/utils/v2dat
# rm -rf feeds/smpackage/{base-files,dnsmasq,firewall*,fullconenat,libnftnl,nftables,ppp,opkg,ucl,upx,vsftpd*,miniupnpd-iptables,wireless-regdb}

# rm -rf feeds/packages/lang/golang
# git clone https://github.com/kenzok8/golang feeds/packages/lang/golang

# rm -rf feeds/kiddin9/luci-lib-taskd
# rm -rf feeds/kiddin9/luci-app-store

rm -rf feeds/packages/lang/ruby
git clone https://github.com/coolsnowwolf/packages tmp/lede-packages
mv tmp/lede-packages/lang/ruby feeds/packages/lang/ruby
# mv tmp/lede-packages/net/gowebdav feeds/packages/net/gowebdav
# mv tmp/lede-packages/utils/bandwidthd feeds/packages/utils/bandwidthd
# mv tmp/lede-packages/net/shadowsocks-libev feeds/packages/net/shadowsocks-libev
# mv tmp/lede-packages/libs/pcre2 feeds/packages/libs/pcre2
# rm -rf tmp/lede-packages
# mv tmp/lede-packages/lang/lua-maxminddb feeds/packages/lang/lua-maxminddb
# mv tmp/lede-packages/net/redsocks2 feeds/packages/net/redsocks2
# mv tmp/lede-packages/net/trojan-plus feeds/packages/net/trojan-plus

# 2024-07-24临时更改 HASH
sed -i "s/PKG_MIRROR_HASH:=ed7c71afb74c8232cfda084545ad8c1f8fe6c5e8176da9a77729e1fa9044d863/PKG_MIRROR_HASH:=skip/" feeds/packages/net/trojan-plus/Makefile
sed -i "s/PKG_MIRROR_HASH:=0981bf49cb8a6e7f81912808987727bf6a2454ad0a3cf744f1a64bfc1969b088/PKG_MIRROR_HASH:=skip/" feeds/packages/net/redsocks2/Makefile
sed -i "s/PKG_MIRROR_HASH:=e70dd8843c3688b58f66fff5320a93d5789b79114bcb36a94d5b554664439f04/PKG_MIRROR_HASH:=skip/" feeds/packages/lang/lua-maxminddb/Makefile
sed -i 's/PKG_MIRROR_HASH:=.*/PKG_MIRROR_HASH:=skip/' feeds/kiddin9/cgroupfs-mount/Makefile

# 处理luci.mk 使正确处理LUCI_LANG.zh-cn 生成中文包
# sed -i "/LUCI_LANG.zh_Hant/a\LUCI_LANG.zh-cn=\$\(LUCI_LANG.zh_Hans\)\nLUCI_LANG.zh-tw=\$\(LUCI_LANG.zh_Hant\)\nLUCI_LANG.en=English" feeds/luci/luci.mk
# sed -i "/LUCI_LC_ALIAS.zh_Hant/a\LUCI_LC_ALIAS.zh-cn=zh-cn\nLUCI_LC_ALIAS.zh-tw=zh-tw" feeds/luci/luci.mk
# sed -i "s/    DEFAULT:=LUCI_LANG_.*/    ifeq \(\$\(2\),zh-cn\)\n        DEFAULT:=LUCI_LANG_zh_Hans||\(ALL\&\&m\)\n    else ifeq \(\$\(2\),zh-tw\)\n        DEFAULT:=LUCI_LANG_zh_Hant||\(ALL\&\&m\)\n    else\n        DEFAULT:=LUCI_LANG_\$\(2\)||\(ALL\&\&m\)\n    endif/"  feeds/luci/luci.mk
# sed -i "/LUCI_BUILD_PACKAGES +=/i\  define Package\/luci-i18n-\$\(LUCI_BASENAME\)-\$\(1\)\/postinst\n\t[ -n "\$\$\$\${IPKG_INSTROOT}" ] || {\n\t\t\(. \/etc\/uci-defaults\/luci-i18n-\$\(LUCI_BASENAME\)-\$\(1\)\) \&\& rm -f \/etc\/uci-defaults\/luci-i18n-\$\(LUCI_BASENAME\)-\$\(1\)\n\t\texit 0\n\t}\n  endef" feeds/luci/luci.mk

# kiddin9 相关的冲突包
rm -rf feeds/packages/net/{alist,mosdns,xray*,v2ray*,v2ray*,smartdns}
rm -rf feeds/packages/utils/v2dat
rm -rf feeds/kiddin9/{base-files,dnsmasq,firewall*,fullconenat,libnftnl,nftables,ppp,opkg,upx,miniupnpd-iptables,wireless-regdb,quectel_SRPD_PCIE,adguardhome,shortcut-fe,fibocom_QMI_WWAN,quectel_QMI_WWAN,rtl8189es,accel-ppp,dockerd,cgroupfs-mount}
mv -f feeds/kiddin9/r81* tmp/
# 替换 quickstart.lua
curl -sL https://raw.githubusercontent.com/kenzok8/openwrt-packages/master/luci-app-quickstart/luasrc/controller/quickstart.lua -o feeds/kiddin9/luci-app-quickstart/luasrc/controller/quickstart.lua

./scripts/feeds install -a -p kiddin9 -f

./scripts/feeds install -a
# mv -f feeds/kiddin9/r81* tmp/
