#!/usr/bin/env python3
# 冒烟测试:真实 chromium 跑 存→赛季筛选→查→复制→删 全流程 + 截图
import json, sys, os
from playwright.sync_api import sync_playwright

URL = os.environ.get("COMPBOX_URL", "file:///home/hkxxzx/comp-box/index.html")
ok = 0; fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += not bool(cond)
    print(("PASS" if cond else "FAIL") + " | " + name)

with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844}, permissions=["clipboard-read", "clipboard-write"])
    pg = ctx.new_page()
    errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL)
    pg.evaluate("localStorage.clear()"); pg.reload()

    CODE = "H4sIAAAAAAAAAOy8VWxbO1Ll2fb5zz+vvvrL7H7/OW/v9/6"
    CODE2 = "H4sIAAAAAAAAAOy8VWxbO1Ll2fb5zz+vvvrL7H7/OW/v9/7"

    # 1. 存 S18:粘贴带名字文案
    pg.click("#fab")
    pg.fill("#raw", "【福星临门】" + CODE)
    pg.click("#btn-save")
    check("存1:S18 列表1条", pg.locator("li.item").count() == 1)
    check("chip 含 S18", pg.locator(".chip", has_text="S18").count() >= 1)
    check("chip 含 全部", pg.locator(".chip", has_text="全部").count() == 1)

    # 2. 存 S17
    pg.click("#fab")
    pg.fill("#raw", CODE2)
    pg.fill("#name", "天将九五")
    pg.fill("#season", "S17")
    pg.click("#btn-save")
    check("存2:S17 列表2条", pg.locator("li.item").count() == 2)
    check("chip 含 S17", pg.locator(".chip", has_text="S17").count() == 1)

    # 3. 赛季筛选:S17 chip → 只见 S17
    pg.locator(".chip", has_text="S17").click()
    check("筛S17 1条", pg.locator("li.item").count() == 1)
    check("筛S17 命中天将九五", "天将九五" in pg.locator("li.item").inner_text())
    check("S17 徽标在卡片上", pg.locator("li.item .tag.season").inner_text() == "S17")
    pg.locator(".chip", has_text="S18").click()
    check("筛S18 1条", pg.locator("li.item").count() == 1)
    check("筛S18 命中福星临门", "福星临门" in pg.locator("li.item").inner_text())
    check("S18 徽标在卡片上", pg.locator("li.item .tag.season").inner_text() == "S18")
    pg.locator(".chip", has_text="全部").click()
    check("回全部 2条", pg.locator("li.item").count() == 2)

    # 4. 搜索与赛季叠加:全部+S18下搜索九五
    pg.fill("#search", "九五")
    check("搜九五 1条", pg.locator("li.item").count() == 1)
    pg.fill("#search", "")
    check("清搜索 2条", pg.locator("li.item").count() == 2)

    # 5. 复制(真实剪贴板权限)
    pg.locator("li.item", has_text="福星临门").locator(".copy").click()
    import time; time.sleep(0.3)
    check("复制到剪贴板", pg.evaluate("navigator.clipboard.readText()") == CODE)

    # 6. 筛选记忆:选 S17 → 重载仍是 S17
    pg.locator(".chip", has_text="S17").click()
    pg.reload()
    check("重载后记住S17筛选", pg.locator("li.item").count() == 1 and "天将九五" in pg.locator("li.item").inner_text())
    pg.locator(".chip", has_text="全部").click()

    # 7. 删除
    pg.on("dialog", lambda d: d.accept())
    pg.locator("li.item", has_text="福星临门").locator(".del").click()
    check("删后剩 1", pg.locator("li.item").count() == 1)
    check("toast 已删除", "已删除" in pg.locator("#toast").inner_text())

    # 8. localStorage 结构断言
    stored = pg.evaluate("JSON.parse(localStorage.getItem('jccCompCodes.v1'))")
    check("localStorage 1条", len(stored) == 1)
    check("season 字段=S17", stored[0]["season"] == "S17")
    check("数据含 ts", isinstance(stored[0]["ts"], (int, float)) and stored[0]["ts"] > 0)

    # 9. 删光该赛季自动回全部
    pg.locator("li.item .del").click()
    check("删光后回全部(无卡死)", pg.locator("li.item").count() == 0)
    check("全部 chip 激活", "全部" in pg.locator("#seasons .chip.on").inner_text())

    # 10. 迁移:旧格式(无 season)数据归当前赛季 S18
    pg.evaluate("localStorage.setItem('jccCompCodes.v1', JSON.stringify([{id:'x1',code:'Abc1234567890Abc',name:'旧数据',tag:'',ts:1}]))")
    pg.reload()
    old = pg.evaluate("JSON.parse(localStorage.getItem('jccCompCodes.v1'))[0]")
    check("旧数据补 season=S18", old["season"] == "S18")
    check("旧数据显示", "旧数据" in pg.locator("li.item").inner_text())

    check("无 console 错误", not [e for e in errs if "favicon" not in e])
    b.close()

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
