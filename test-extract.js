// extract() 单测:从 comp-box.html 内联 JS 中取出纯函数执行(无 DOM 依赖)
const fs = require("fs");
const html = fs.readFileSync(__dirname + "/index.html", "utf8");
const js = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const start = js.indexOf("function extract(");
const end = js.indexOf("function makeItem(");
if (start < 0 || end < 0) { console.error("FAIL: extract 函数未找到"); process.exit(1); }
eval(js.slice(start, end)); // 定义 extract

// 真实码模拟:【阵容码】H4sI 开头 base64/gzip 长串
const CODE = "H4sIAAAAAAAAAOy8VWxbO1Ll2fb5zz+vvvrL7H7/OW/v9/6/f/77/vnv//f93nvvvf+/";
let pass = 0, fail = 0;
function eq(name, got, want) {
  const ok = got === want;
  ok ? pass++ : fail++;
  console.log((ok ? "PASS" : "FAIL") + " | " + name + "\n     got: " + JSON.stringify(got) + "\n     exp: " + JSON.stringify(want));
}
function t(name, input, expCode, expName) {
  const r = extract(input);
  eq(name + " [code]", r.code, expCode);
  eq(name + " [name]", r.name, expName);
}

// 1. 游戏内分享全文(【阵容码】+码,无空格粘连)
t("游戏分享单token",
  "【阵容码】" + CODE,
  CODE, "");
// 2. 无空格:【阵容名】+码 粘连(公众号/图集常见)
t("阵容名+码粘连",
  "【福星临门】" + CODE,
  CODE, "福星临门");
// 3. B站简介多行文案
t("B站文案多行",
  "星神版本答案!\n阵容码:" + CODE + "\n林小北 金铲铲700 出品",
  CODE, "星神版本答案! 林小北 金铲铲700 出品");
// 4. 空格分隔:名字 码 模式
t("名字空格码",
  "天将九五 " + CODE + " 上分",
  CODE, "天将九五 上分");
// 5. 纯码
t("纯码", CODE, CODE, "");
// 6. 无码文本
t("无码", "今天玩什么阵容好呢", "", "今天玩什么阵容好呢");
// 7. 短字母词不当码
t("短词不当码", "九五 天将 abc12345678", "", "九五 天将 abc12345678");
// 8. 空
t("空", "   ", "", "");
// 9. 名字文字裹码(无任何空格,名字在码后)
t("码后中文粘连",
  CODE + "速冲分",
  CODE, "速冲分");
// 10. 名字含 ASCII 短词/数字不当码;同码重复粘贴不污染名字
t("名字含短词+重复码",
  "6级追三星 天将福星 " + CODE + " " + CODE,
  CODE, "6级追三星 天将福星");

console.log("\n" + pass + " passed, " + fail + " failed");
process.exit(fail ? 1 : 0);
