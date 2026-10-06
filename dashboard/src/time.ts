// 页面层：时间展示。后端一律给 UTC，页面按访问者本地时区渲染并标出偏移。

function pad2(value: number): string {
  // 补两位，让 3 时显示成 03
  return String(value).padStart(2, "0");
}

export function timezoneLabel(moment: Date): string {
  // 浏览器把偏移量记成「本地比 UTC 快多少」的相反数，符号要反过来
  const offsetMinutes = -moment.getTimezoneOffset();
  const sign = offsetMinutes < 0 ? "-" : "+";
  const absolute = Math.abs(offsetMinutes);
  return "UTC" + sign + pad2(Math.floor(absolute / 60)) + ":" + pad2(absolute % 60);
}

export function showTime(value: string): string {
  // 空值就写无。解析不了就原样显示，不要把 Invalid Date 露出来
  if (!value) {
    return "无";
  }
  const moment = new Date(value);
  if (Number.isNaN(moment.getTime())) {
    return value;
  }
  const local =
    moment.getFullYear() +
    "-" +
    pad2(moment.getMonth() + 1) +
    "-" +
    pad2(moment.getDate()) +
    " " +
    pad2(moment.getHours()) +
    ":" +
    pad2(moment.getMinutes()) +
    ":" +
    pad2(moment.getSeconds());
  return local + "（" + timezoneLabel(moment) + "）";
}

export function rawUtcTitle(value: string): string | undefined {
  // 没值就不给 tooltip，免得悬停出现空白
  if (!value) {
    return undefined;
  }
  return "后端 UTC：" + value;
}

export function showRate(value: number | null): string {
  // rounded_24h / rounded_48h 是 0 到 100 的百分数，没有就说明来源没给
  if (value === null || value === undefined) {
    return "来源没给";
  }
  return String(value) + "%";
}
