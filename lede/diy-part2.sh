#!/bin/bash
# ==============================================================
# Copyright (c) 2019-2020 P3TERX <https://p3terx.com>
#
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#
# https://github.com/P3TERX/Actions-OpenWrt
# File name: diy-part2.sh
# Description: OpenWrt DIY script part 2 (After Update feeds)
# ===============================================================


#修改默认IP
sed -i 's/192.168.1.1/192.168.1.21/g' package/base-files/files/bin/config_generate   # 定制默认IP
sed -i 's/192.168.1.1/192.168.1.21/g' package/feeds/kiddin9/base-files/files/bin/config_generate
# 默认网关
# uci set network.lan.gateway='192.168.1.1'
# uci set network.lan.dns='192.168.1.1'
sed -i 's/\(\([ \t]\+\)set network.$1.netmask=.*\)/\1\n \2set network.$1.dns='192.168.1.1'/' package/base-files/files/bin/config_generate
sed -i 's/\(\([ \t]\+\)set network.$1.netmask=.*\)/\1\n \2set network.$1.gateway='192.168.1.1'/' package/base-files/files/bin/config_generate
sed -i 's/\(\([ \t]\+\)set network.$1.netmask=.*\)/\1\n \2set network.$1.dns='192.168.1.1'/' package/feeds/kiddin9/base-files/files/bin/config_generate
sed -i 's/\(\([ \t]\+\)set network.$1.netmask=.*\)/\1\n \2set network.$1.gateway='192.168.1.1'/' package/feeds/kiddin9/base-files/files/bin/config_generate

# 更改默认 Shell 为 bash
sed -i 's/\/bin\/ash/\/bin\/bash/g' package/base-files/files/etc/passwd

# opkg源
sed -i "/mirrors.tencent.com/d" package/lean/default-settings/files/zzz-default-settings
sed -i "/18.06.9/d" package/lean/default-settings/files/zzz-default-settings

# Configure pppoe connection
#uci set network.wan.proto=pppoe
#uci set network.wan.username='yougotthisfromyour@isp.su'
#uci set network.wan.password='yourpassword'

# 修改软件包
#chmod -R 755 files
#rm -rf feeds/luci/applications/luci-app-mosdns && rm -rf feeds/packages/net/{alist,adguardhome,smartdns}
#rm -rf feeds/smpackage/{base-files,dnsmasq,firewall*,fullconenat,libnftnl,nftables,ppp,opkg,ucl,upx,vsftpd-alt,miniupnpd-iptables,wireless-regdb}
#rm -rf feeds/packages/lang/golang
#git clone https://github.com/kenzok8/golang feeds/packages/lang/golang


# 停用冲突的软件包: luci-app-smartdns换为需要操作的包名，启用=y， 停用=n
# sed -i "s/\(luci-app-smartdns\)=y/\1=n/" .config
# sed -i 's/\(luci-app-bypass\)=y/\1=n/' .config
# sed -i 's/\(luci-app-passwall\)=y/\1=n/' .config
# sed -i 's/\(luci-app-ssr-plus\)=y/\1=n/' .config
# 2024-07-17 chinadns-ng, hash检查不通过，临时取消相关包
# sed -i 's/\(luci-app-passwall\)=y/\1=n/' .config
# sed -i 's/\(luci-app-ssr-plus\)=y/\1=n/' .config
# sed -i 's/\(chinadns-ng\)=y/\1=n/' .config

# 添加额外软件包
echo 'CONFIG_PACKAGE_luci-app-diskman=y' >>.config
echo 'CONFIG_PACKAGE_luci-app-samba4=y' >>.config
echo 'CONFIG_PACKAGE_docker-compose=y' >>.config
echo 'CONFIG_PACKAGE_luci-app-dockerman=y' >>.config
echo 'CONFIG_PACKAGE_luci-app-istorex=y' >>.config
echo 'CONFIG_PACKAGE_luci-app-linkease=y' >>.config
echo 'CONFIG_PACKAGE_luci-app-gowebdav=y' >>.config
echo 'CONFIG_PACKAGE_kmod-fs-virtiofs=n' >>.config
echo 'CONFIG_PACKAGE_kmod-usb-audio=n' >>.config
echo 'CONFIG_PACKAGE_quectel_SRPD_PCIE=n' >>.config


# 科学上网插件


# 科学上网插件依赖
