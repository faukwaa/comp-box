#!/usr/bin/env python3
# 冒烟测试:真实 chromium 跑 存→剪贴板→赛季→选择模式批量删→标签筛选→云同步 全流程
import json, sys, os, base64, time
from playwright.sync_api import sync_playwright

URL = os.environ.get("COMPBOX_URL", "file:///home/hkxxzx/comp-box/index.html")
ok = 0; fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += not bool(cond)
    print(("PASS" if cond else "FAIL") + " | " + name)
def waitfor(fn, timeout=6, interval=0.1):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if fn(): return True
        except Exception:
            pass
        time.sleep(interval)
    return False

with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844}, permissions=["clipboard-read", "clipboard-write"])
    # 测试隔离:默认关闭云端(页面嵌入了真 token,测试不能真连 GitHub;12 段显式注入 mock token)
    ctx.add_init_script("try{ if(!localStorage.getItem('ccToken')) localStorage.setItem('ccToken',''); }catch(e){}")
    pg = ctx.new_page()
    errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL)
    pg.evaluate("localStorage.clear()"); pg.reload()

    CODE = "H4sIAAAAAAAAAOy8VWxbO1Ll2fb5zz+vvvrL7H7/OW/v9/6"
    CODE2 = CODE[:-1] + "7"

    # 1. 存 S18:粘贴带名字文案
    pg.click("#fab")
    pg.fill("#raw", "【福星临门】" + CODE)
    pg.click("#btn-save")
    check("存1:S18 列表1条", pg.locator("li.item").count() == 1)
    check("chip 含 S18", pg.locator("#seasons .chip", has_text="S18").count() >= 1)
    check("选择按钮出现", pg.locator("#select-btn").is_visible())

    # 1c. grabber 下拉 / 点击 关闭表单
    pg.click("#fab")
    pg.wait_for_timeout(450)  # 等 sheet 弹出动画完成再拖
    check("表单打开", pg.locator("#sheet.open").count() == 1)
    gb = pg.locator("#sheet-grab").bounding_box()
    pg.mouse.move(gb["x"] + gb["width"] / 2, gb["y"] + gb["height"] / 2)
    pg.mouse.down()
    pg.mouse.move(gb["x"] + gb["width"] / 2, gb["y"] + gb["height"] / 2 + 240, steps=8)
    pg.mouse.up()
    check("下拉关闭表单", waitfor(lambda: pg.locator("#sheet.open").count() == 0))
    pg.click("#fab")
    pg.locator("#sheet-grab").click()
    check("点击横线关闭表单", waitfor(lambda: pg.locator("#sheet.open").count() == 0))

    # 1b. 点「从剪贴板粘贴」按钮读取
    pg.evaluate(f"navigator.clipboard.writeText('【星神】{CODE}')")
    pg.click("#fab")
    pg.click("#btn-paste")
    check("粘贴按钮读入 raw", waitfor(lambda: pg.input_value("#raw") == f"【星神】{CODE}", timeout=5))
    check("粘贴自动带出名字", pg.input_value("#name") == "星神")
    pg.click("#btn-save")
    check("存2:剪贴板流程入库", pg.locator("li.item").count() == 2)

    # 2. 存 S17(手动输入不被剪贴板自动读覆盖)
    pg.click("#fab")
    pg.fill("#raw", CODE2)
    pg.fill("#name", "天将九五")
    pg.fill("#season", "S17")
    pg.wait_for_timeout(400)
    check("手动输入不被剪贴板覆盖", pg.input_value("#raw") == CODE2)
    pg.click("#btn-save")
    check("存3:S17 列表3条", pg.locator("li.item").count() == 3)

    # 3. 赛季筛选
    pg.locator("#seasons .chip", has_text="S17").click()
    check("筛S17 1条", pg.locator("li.item").count() == 1)
    check("筛S17 命中天将九五", "天将九五" in pg.locator("li.item", has_text="天将九五").inner_text())
    pg.locator("#seasons .chip", has_text="S18").click()
    check("筛S18 2条", pg.locator("li.item").count() == 2)
    check("S18 徽标在卡片上", pg.locator("li.item .tag.season").first.inner_text() == "S18")
    pg.locator("#seasons .chip", has_text="全部").click()
    check("回全部 3条", pg.locator("li.item").count() == 3)

    # 4. 搜索
    pg.fill("#search", "九五")
    check("搜九五 1条", pg.locator("li.item").count() == 1)
    pg.fill("#search", "")
    check("清搜索 3条", pg.locator("li.item").count() == 3)

    # 5. 常态点整行=复制
    pg.locator("li.item", has_text="福星临门").locator(".item-content").click()
    import time; time.sleep(0.3)
    check("点行复制到剪贴板", pg.evaluate("navigator.clipboard.readText()") == CODE)
    check("复制 toast", "已复制" in pg.locator("#toast").inner_text())

    # 5b. 左滑露出删除(鼠标模拟滑动)
    li = pg.locator("li.item", has_text="星神")
    box = li.bounding_box()
    pg.mouse.move(box["x"] + box["width"] * 0.7, box["y"] + box["height"] / 2)
    pg.mouse.down()
    pg.mouse.move(box["x"] + box["width"] * 0.7 - 140, box["y"] + box["height"] / 2, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(300)  # 等 snap 动画 + click 抑制窗口
    check("左滑露出删除按钮", li.evaluate("el => el.classList.contains('open')"))
    check("左滑后未误复制", "星神" not in pg.locator("#toast").inner_text())
    # 右滑收回:从露出的红区(删除按钮上)起手右滑
    box2 = li.bounding_box()
    pg.mouse.move(box2["x"] + box2["width"] - 30, box2["y"] + box2["height"] / 2)
    pg.mouse.down()
    pg.mouse.move(box2["x"] + box2["width"] - 30 + 160, box2["y"] + box2["height"] / 2, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(300)
    check("右滑收回", li.evaluate("el => !el.classList.contains('open')"))
    check("右滑未误删", pg.locator("li.item").count() == 3)
    # 重新左滑 → 点删除 → 单删确认
    box3 = li.bounding_box()
    pg.mouse.move(box3["x"] + box3["width"] * 0.7, box3["y"] + box3["height"] / 2)
    pg.mouse.down()
    pg.mouse.move(box3["x"] + box3["width"] * 0.7 - 140, box3["y"] + box3["height"] / 2, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(300)
    li.locator(".swipe-del").click()
    check("单删确认文案含名字", "删除「星神」" in pg.locator("#confirm-msg").inner_text())
    pg.locator("#cf-ok").click()
    check("滑动删除后剩2", pg.locator("li.item").count() == 2)
    check("确认删除后滑条收起", pg.locator("li.item.open").count() == 0)

    # 6. 筛选记忆
    pg.locator("#seasons .chip", has_text="S17").click()
    pg.reload()
    check("重载记住S17筛选", pg.locator("li.item").count() == 1 and "天将九五" in pg.locator("li.item").inner_text())
    pg.locator("#seasons .chip", has_text="全部").click()

    # 7. 选择模式:点勾选圈勾选 → 底部删除(1) → 确认弹层 → 删除
    pg.click("#select-btn")
    check("进入选择模式", pg.evaluate("document.body.classList.contains('select-mode')"))
    check("未选行不变灰", pg.evaluate("getComputedStyle(document.querySelector('li.item:not(.sel)')).opacity") == "1")
    check("选择模式行出现勾选圈", pg.locator("li.item .check").first.is_visible())
    pg.locator("li.item", has_text="福星临门").locator(".check").click()
    pg.wait_for_timeout(250)  # 等勾选圈 0.15s 过渡完成
    check("点勾选圈后行高亮", "sel" in pg.locator("li.item", has_text="福星临门").get_attribute("class"))
    check("勾选圈黑色主题", pg.evaluate("getComputedStyle(document.querySelector('li.item.sel .check')).backgroundColor") == "rgb(28, 28, 30)")
    check("选择按钮黑色主题", pg.evaluate("getComputedStyle(document.getElementById('select-btn')).color") == "rgb(28, 28, 30)")
    check("计数显示已选1", "已选 1" in pg.locator("#count").inner_text())
    check("删除按钮文案", pg.locator("#sb-delete").inner_text() == "删除(1)")
    pg.locator("#sb-delete").click()
    check("确认弹层出现", pg.locator("#confirm-sheet.open").count() == 1)
    check("确认文案含名字", "删除「福星临门」" in pg.locator("#confirm-msg").inner_text())
    pg.locator("#cf-ok").click()
    check("确认删除后剩1", pg.locator("li.item").count() == 1)
    check("仍在选择模式(未删光)", pg.evaluate("document.body.classList.contains('select-mode')"))
    check("删除后计数复位", "选择阵容" in pg.locator("#count").inner_text())

    # 8. localStorage 结构
    stored = pg.evaluate("JSON.parse(localStorage.getItem('jccCompCodes.v1'))")
    check("localStorage 1条", len(stored) == 1)
    s17 = [x for x in stored if x["code"] == CODE2][0]
    check("S17 条目 season=S17", s17["season"] == "S17")
    check("S17 条目 ts 正常", isinstance(s17["ts"], (int, float)) and s17["ts"] > 1e12)

    # 9. 全选删除 → 删光自动退出选择模式
    pg.click("#sb-selectall")
    check("全选后删除(1)", pg.locator("#sb-delete").inner_text() == "删除(1)")
    check("全选按钮变取消全选", "取消全选" in pg.locator("#sb-selectall").inner_text())
    pg.locator("#sb-delete").click()
    check("确认文案-全部", "删除 全部阵容" in pg.locator("#confirm-msg").inner_text())
    pg.locator("#cf-ok").click()
    check("删光列表空", pg.locator("li.item").count() == 0)
    check("删光自动退出选择", not pg.evaluate("document.body.classList.contains('select-mode')"))
    check("退出后选择按钮回文案", pg.locator("#select-btn").inner_text() == "选择")
    check("退出后 FAB 可见", pg.locator("#fab").is_visible())
    check("全部 chip 激活", "全部" in pg.locator("#seasons .chip.on").inner_text())

    # 10. 旧数据(无 season)迁移归当前赛季
    pg.evaluate("localStorage.setItem('jccCompCodes.v1', JSON.stringify([{id:'x1',code:'Abc1234567890Abc',name:'旧数据',tag:'',ts:1}]))")
    pg.reload()
    old = pg.evaluate("JSON.parse(localStorage.getItem('jccCompCodes.v1'))[0]")
    check("旧数据补 season=S18", old["season"] == "S18")
    check("旧数据显示", "旧数据" in pg.locator("li.item").inner_text())

    # 11. 标签筛选:塞 4 条带标签数据
    pg.evaluate(f"""localStorage.setItem('jccCompCodes.v1', JSON.stringify([
      {{id:'a1',code:'{CODE}',name:'福星回归',tag:'追三星',season:'S18',ts:Date.now()}},
      {{id:'a2',code:'{CODE2}',name:'天将九五',tag:'追三星',season:'S17',ts:Date.now()-1}},
      {{id:'a3',code:'{CODE}',name:'裁决婕拉',tag:'上分',season:'S18',ts:Date.now()-2}},
      {{id:'a4',code:'{CODE2}',name:'零标签阵容',tag:'',season:'S18',ts:Date.now()-3}}
    ]))""")
    pg.reload()
    check("标签开关出现(默认折叠)", pg.locator("#tag-toggle").is_visible() and pg.locator("#tag-toggle").evaluate("el => el.classList.contains('open')") == False)
    check("标签行初始收起", not pg.locator("#tag-chips").is_visible())
    pg.click("#tag-toggle")  # 展开标签行
    check("标签行展开", pg.locator("#tag-chips").is_visible() and "open" in pg.locator("#tag-toggle").get_attribute("class"))
    check("chips 含追三星", pg.locator("#tag-chips .chip", has_text="追三星").count() == 1)
    check("chips 含上分", pg.locator("#tag-chips .chip", has_text="上分").count() == 1)
    check("全部4条可见", pg.locator("li.item").count() == 4)
    # 点标签 chip 筛"追三星"
    pg.locator("#tag-chips .chip", has_text="追三星").click()
    check("筛追三星 2条", pg.locator("li.item").count() == 2)
    check("chips 追三星高亮", "on" in pg.locator("#tag-chips .chip", has_text="追三星").get_attribute("class"))
    check("激活标签时开关显示标签名", "追三星" in pg.locator("#tag-toggle-label").inner_text())
    # 与赛季叠加:S17
    pg.locator("#seasons .chip", has_text="S17").click()
    check("追三星+S17 1条", pg.locator("li.item").count() == 1)
    check("组合命中天将", "天将九五" in pg.locator("li.item").inner_text())
    check("计数显示双条件", "S17" in pg.locator("#count").inner_text() and "追三星" in pg.locator("#count").inner_text())
    # 点卡片上 tag 徽章=取消标签筛选(season 保留)
    pg.locator("li.item .tag:not(.season)").click()
    check("点徽章取消标签筛", pg.locator("li.item").count() == 1)
    check("赛季筛仍保留", "S17" in pg.locator("#count").inner_text())
    check("全部标签 chip 高亮", "on" in pg.locator("#tag-chips .chip", has_text="全部标签").get_attribute("class"))
    # 点卡片上 season 徽章=取消赛季筛选
    pg.locator("li.item .tag.season").click()
    check("点赛季徽章取消赛季筛", pg.locator("li.item").count() == 4)
    # 从 chips 行选中标签后点卡片徽章切到同标签=取消;这里验证点 season 徽章能直接启用赛季筛选
    pg.locator("li.item", has_text="裁决婕拉").locator(".tag.season").click()
    check("点赛季徽章启用S18筛", pg.locator("li.item").count() == 3 and "S18" in pg.locator("#count").inner_text())
    pg.locator("li.item", has_text="裁决婕拉").locator(".tag:not(.season)").click()
    check("点标签徽章启用上分筛", pg.locator("li.item").count() == 1 and "上分" in pg.locator("#count").inner_text())
    check("S18+上分 命中裁决", "裁决婕拉" in pg.locator("li.item").inner_text())

    # 11b. 左滑编辑阵容
    pg.locator("#seasons .chip", has_text="全部").click()
    pg.locator("#tag-chips .chip", has_text="全部标签").click()
    li_e = pg.locator("li.item", has_text="裁决婕拉")
    bx = li_e.bounding_box()
    pg.mouse.move(bx["x"] + bx["width"] * 0.7, bx["y"] + bx["height"] / 2)
    pg.mouse.down(); pg.mouse.move(bx["x"] + bx["width"] * 0.7 - 200, bx["y"] + bx["height"] / 2, steps=8); pg.mouse.up()
    pg.wait_for_timeout(300)
    check("左滑露出编辑+删除", li_e.locator(".swipe-edit").is_visible() and li_e.locator(".swipe-del").is_visible())
    li_e.locator(".swipe-edit").click()
    check("编辑表单标题", pg.locator("#sheet-title").inner_text() == "编辑阵容")
    check("编辑预填名字", pg.input_value("#name") == "裁决婕拉")
    check("编辑预填赛季", pg.input_value("#season") == "S18")
    check("编辑预填码", pg.input_value("#raw").startswith(CODE[:10]))
    pg.fill("#name", "裁决新名")
    pg.fill("#tag", "烂分")
    pg.click("#btn-save")
    check("保存更新 toast", waitfor(lambda: "已更新" in pg.locator("#toast").inner_text()))
    check("列表显示新名字", "裁决新名" in pg.locator("#list").inner_text())
    check("原名字消失", "裁决婕拉" not in pg.locator("#list").inner_text())
    check("编辑后条数不变", pg.locator("li.item").count() == 4)

    # 11c. 收藏置顶
    pg.locator("li.item", has_text="零标签阵容").locator(".fav-btn").click()
    check("收藏 toast", waitfor(lambda: "已收藏" in pg.locator("#toast").inner_text()))
    check("收藏后置顶", "零标签阵容" in pg.locator("li.item").first.inner_text())
    check("置顶行带星标", pg.locator("li.item").first.locator(".fav-btn.on").count() == 1)
    check("原首位后移", pg.locator("li.item").nth(1).inner_text().find("福星回归") >= 0 or "福星回归" in pg.locator("li.item").nth(1).inner_text())
    # 取消收藏 → 回原顺序(ts 最小者殿后)
    pg.locator("li.item").first.locator(".fav-btn").click()
    check("取消收藏 toast", waitfor(lambda: "取消收藏" in pg.locator("#toast").inner_text()))
    check("取消后回到末位", "零标签阵容" in pg.locator("li.item").last.inner_text())
    check("无置顶星标残留", pg.locator(".fav-btn.on").count() == 0)

    # 12. 云同步(真实本地 HTTP 服务器模拟 GitHub contents API)
    import http.server, threading
    GH = {"sha": "sha0", "items": [], "ver": 0, "lock": threading.Lock()}
    class GHSrv(http.server.BaseHTTPRequestHandler):
        def _hdr(self, code, ctype="application/json", body=""):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("Access-Control-Allow-Methods", "*")
            self.end_headers()
            if body: self.wfile.write(body.encode() if isinstance(body, str) else body)
        def do_OPTIONS(self): self._hdr(204, "", "")
        def do_GET(self):
            with GH["lock"]:
                doc = {"sha": GH["sha"], "content": base64.b64encode(
                    json.dumps({"v": 1, "items": GH["items"]}, ensure_ascii=False).encode()).decode()}
            self._hdr(200, body=json.dumps(doc))
        def do_PUT(self):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode() or "{}")
            with GH["lock"]:
                if body.get("sha") and body["sha"] != GH["sha"]:
                    self._hdr(409, body='{"message":"conflict"}'); return
                items = json.loads(base64.b64decode(body["content"]).decode())["items"]
                GH["items"] = items; GH["ver"] += 1; GH["sha"] = "sha" + str(GH["ver"])
            self._hdr(200, body=json.dumps({"content": {"sha": GH["sha"]}}))
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), GHSrv)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    api_base = f"http://127.0.0.1:{srv.server_address[1]}/"
    # 干净起步:通过 UI 设置面板配 token(API 指向本地服务器),保存后自动同步
    pg.evaluate(f"localStorage.clear(); localStorage.setItem('ccApiBase','{api_base}');")
    pg.reload()
    pg.click("#sync-btn")                            # 未配置 → 打开令牌设置
    check("点同步按钮打开令牌设置", pg.locator("#token-sheet.open").count() == 1)
    pg.fill("#cc-token-input", "mocktoken0123456789abcdef")
    pg.click("#btn-token-save")
    pg.wait_for_timeout(1200)                        # 保存触发 reload+同步
    check("同步按钮显示", waitfor(lambda: pg.locator("#sync-btn.ok").count() == 1))
    # 12a. 保存 → 自动推云端
    pg.click("#fab"); pg.fill("#raw", "【云端一号】" + CODE); pg.click("#btn-save")
    check("保存自动上云", waitfor(lambda: len(GH["items"]) == 1 and GH["items"][0]["name"] == "云端一号"))
    # 12b. 别端新增(模拟我电脑端 git 提交)→ 手动同步拉取合并
    GH["items"].append({"id": "remote1", "code": CODE2, "name": "电脑端阵容", "tag": "上分", "season": "S18", "ts": int(time.time() * 1000) + 1})
    GH["ver"] += 1; GH["sha"] = "sha" + str(GH["ver"])
    pg.click("#sync-btn")
    check("拉取别端新增", waitfor(lambda: "电脑端阵容" in pg.locator("#list").inner_text()))
    check("合并后仍保留本端", pg.locator("li.item").count() == 2)
    # 12c. 删除 → 传播到云端
    li12 = pg.locator("li.item", has_text="云端一号")
    bx = li12.bounding_box()
    pg.mouse.move(bx["x"] + bx["width"] * 0.7, bx["y"] + bx["height"] / 2)
    pg.mouse.down(); pg.mouse.move(bx["x"] + bx["width"] * 0.7 - 140, bx["y"] + bx["height"] / 2, steps=6); pg.mouse.up()
    pg.wait_for_timeout(300)
    li12.locator(".swipe-del").click()
    pg.locator("#cf-ok").click()
    check("删除传播到云端", waitfor(lambda: len(GH["items"]) == 1 and GH["items"][0]["id"] == "remote1"))
    # 12d. 409 冲突:别端在本地不知情时改云 → 本地保存触发冲突 → 自动合并两端新增
    GH["items"].append({"id": "remote2", "code": CODE, "name": "别端新阵容", "tag": "", "season": "S18", "ts": int(time.time() * 1000) + 2})
    GH["ver"] += 1; GH["sha"] = "sha" + str(GH["ver"])   # 本地 sync meta 的 sha 已过期
    pg.click("#fab"); pg.fill("#raw", "【本地新阵容】" + CODE2); pg.click("#btn-save")
    check("冲突自动合并(云端含两端新增)", waitfor(lambda: len(GH["items"]) == 3 and
        any(x["name"] == "别端新阵容" for x in GH["items"]) and any(x["name"] == "本地新阵容" for x in GH["items"])))
    check("合并后本地 3 条", pg.locator("li.item").count() == 3)
    check("同步按钮回到绿色", waitfor(lambda: pg.locator("#sync-btn.ok").count() == 1))
    srv.shutdown()
    pg.evaluate("localStorage.removeItem('ccToken'); localStorage.removeItem('ccApiBase')")

    check("无 console 错误", not [e for e in errs if "favicon" not in e and "409" not in e])
    b.close()

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
