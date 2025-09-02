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


# 下载并更新软件源
#shopt -s extglob
# 添加软件源
sed -i '$a src-git kiddin9 https://github.com/kiddin9/openwrt-packages.git;master' feeds.conf.default

# sed -i '1i src-git kenzo https://github.com/kenzok8/openwrt-packages' feeds.conf.default
# sed -i '2i src-git small https://github.com/kenzok8/small' feeds.conf.default
# sed -i '$a src-git smpackage https://github.com/kenzok8/small-package' feeds.conf.default
 
sed -i "/telephony/d" feeds.conf.default
sed -i "s?targets/%S/packages?targets/%S/\$(LINUX_VERSION)?" include/feeds.mk
sed -i '/	refresh_config();/d' scripts/feeds

# 修改 Makefile
find package/*/ -maxdepth 2 -path "*/Makefile" | xargs -i sed -i 's/..\/..\/luci.mk/$(TOPDIR)\/feeds\/luci\/luci.mk/g' {}
find package/*/ -maxdepth 2 -path "*/Makefile" | xargs -i sed -i 's/..\/..\/lang\/golang\/golang-package.mk/$(TOPDIR)\/feeds\/packages\/lang\/golang\/golang-package.mk/g' {}
find package/*/ -maxdepth 2 -path "*/Makefile" | xargs -i sed -i 's/PKG_SOURCE_URL:=@GHREPO/PKG_SOURCE_URL:=https:\/\/github.com/g' {}
find package/*/ -maxdepth 2 -path "*/Makefile" | xargs -i sed -i 's/PKG_SOURCE_URL:=@GHCODELOAD/PKG_SOURCE_URL:=https:\/\/codeload.github.com/g' {}

./scripts/feeds update -a

# git clone https://github.com/kenzok8/small 
# rm -rf feeds/kiddin9/gn
# mv small/gn feeds/kiddin9/gn
# rm -rf small
# ./scripts/feeds install -a -p kiddin9 -f


# 取消对 samba4 的菜单调整
sed -i '/samba4/s/^/#/' package/lean/default-settings/files/zzz-default-settings

# Themes
rm -rf feeds/luci/themes/luci-theme-argon
#rm -rf feeds/luci/themes/luci-theme-bootstrap-mmdvm
git clone -b 18.06 https://github.com/jerrykuku/luci-theme-argon.git package/lean/luci-theme-argon
# 替换默认主题为 luci-theme-argon
# sed -i 's/luci-theme-bootstrap/luci-theme-argon/' feeds/luci/collections/luci/Makefile

# 晶晨宝盒
# rm -rf package/luci-app-amlogic
# git clone https://github.com/ophub/luci-app-amlogic.git package/luci-app-amlogic
# sed -i "s|firmware_repo.*|firmware_repo 'https://github.com/carycoti/OpenWrt-FastRhino-r68s-r66s'|g" package/luci-app-amlogic/root/etc/config/amlogic

# 2024-07-24临时更改 HASH
sed -i "s/PKG_MIRROR_HASH:=ed7c71afb74c8232cfda084545ad8c1f8fe6c5e8176da9a77729e1fa9044d863/PKG_MIRROR_HASH:=skip/" feeds/packages/net/trojan-plus/Makefile
sed -i "s/PKG_MIRROR_HASH:=0981bf49cb8a6e7f81912808987727bf6a2454ad0a3cf744f1a64bfc1969b088/PKG_MIRROR_HASH:=skip/" feeds/packages/net/redsocks2/Makefile
sed -i "s/PKG_MIRROR_HASH:=e70dd8843c3688b58f66fff5320a93d5789b79114bcb36a94d5b554664439f04/PKG_MIRROR_HASH:=skip/" feeds/packages/lang/lua-maxminddb/Makefile

# rm -rf feeds/luci/applications/luci-app-mosdns
# rm -rf feeds/packages/net/{alist,adguardhome,mosdns,xray*,v2ray*,v2ray*,sing*,smartdns,jool}
# rm -rf feeds/packages/utils/{v2dat,gl-mifi-mcu}
# rm -rf feeds/packages/libs/{dmx_usb_module,libpfring}
# rm -rf package/lean/r8101
# rm -rf package/wwan/driver/quectel_SRPD_PCIE
# rm -rf package/kernel/{ath10k-ct,ubnt-ledbar,mac80211}
# rm -rf feeds/routing/batman-adv
# rm -rf feeds/smpackage/{base-files,dnsmasq,firewall*,fullconenat,libnftnl,nftables,ppp,opkg,ucl,upx,vsftpd*,miniupnpd-iptables,wireless-regdb}

rm -rf feeds/packages/lang/golang
git clone https://github.com/kenzok8/golang feeds/packages/lang/golang

# 替换编译出错的包
# rm -rf feeds/packages/net/curl
# rm -rf feeds/packages/libs/glib2
# rm -rf feeds/packages/lang/python/python3
# git clone https://github.com/coolsnowwolf/packages tmp/lede-packages
# mv tmp/lede-packages/net/curl feeds/packages/net/curl
# mv tmp/lede-packages/libs/glib2 feeds/packages/libs/glib2
# mv tmp/lede-packages/lang/python/python3 feeds/packages/lang/python/python3

# 临时更改HASH为跳过检查
# sed -i "s/PKG_HASH:=d907398d08a2cadd8ab5b3c6c353de572bddb87db1363a458703dd7e966ddb13/PKG_HASH:=skip/" feeds/small/chinadns-ng/Makefile

# kiddin9 相关的冲突包
rm -rf feeds/packages/net/{alist,mosdns,xray*,v2ray*,v2ray*,smartdns}
rm -rf feeds/packages/utils/v2dat
rm -rf feeds/kiddin9/{base-files,dnsmasq,firewall*,fullconenat,libnftnl,nftables,ppp,opkg,upx,miniupnpd-iptables,wireless-regdb,quectel_SRPD_PCIE,adguardhome,shortcut-fe,fibocom_QMI_WWAN,quectel_QMI_WWAN,rtl8189es,cgroupfs-mount}
mv -f feeds/kiddin9/r81* tmp/
# 替换 quickstart.lua
curl -sL https://raw.githubusercontent.com/kenzok8/openwrt-packages/master/luci-app-quickstart/luasrc/controller/quickstart.lua -o feeds/kiddin9/luci-app-quickstart/luasrc/controller/quickstart.lua

./scripts/feeds install -a -p kiddin9 -f

./scripts/feeds install -a

# mv -f feeds/kiddin9/r81* tmp/
