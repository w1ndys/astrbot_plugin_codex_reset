// 页面脚本：通过 AstrBot 注入的 bridge 做群列表增删改查。不直接访问父页面。

const bridge = window.AstrBotPluginPage;
const groupIdInput = document.getElementById("group-id");
const remarkInput = document.getElementById("remark");
const enabledInput = document.getElementById("enabled");
const addButton = document.getElementById("add");
const refreshButton = document.getElementById("refresh");
const formError = document.getElementById("form-error");
const groupsBox = document.getElementById("groups");
const statusBox = document.getElementById("status");

function showFormError(message) {
  // 把校验失败留在表单下，不弹窗。
  formError.textContent = message;
}

function fieldValue(input) {
  // 读输入框。缺节点时当空串，避免页面半残时抛错。
  if (!input) {
    return "";
  }
  return String(input.value || "").trim();
}

function pushLabel(row) {
  // 把能不能推翻译成页面上的一句人话。
  if (!row.enabled) {
    return "已关闭";
  }
  if (!row.can_push) {
    return "已开启，但还不能推送。请在插件配置填写平台 ID，或等这个群先来一条消息。";
  }
  if (row.has_session) {
    return "可推送（已见到群消息）";
  }
  return "可推送（用平台 ID 拼会话）";
}

function renderGroups(groups) {
  // 重画群列表。空表就是默认关，不要显示成加载失败。
  groupsBox.textContent = "";
  if (!groups || groups.length === 0) {
    groupsBox.textContent = "还没有群。没添加的群不会收到推送。";
    return;
  }
  for (const row of groups) {
    groupsBox.appendChild(renderRow(row));
  }
}

function renderRow(row) {
  // 画一行：群号、状态、备注、开关、保存和删除。
  const box = document.createElement("div");
  box.className = "row";
  const title = document.createElement("strong");
  title.textContent = row.group_id;
  const state = document.createElement("p");
  state.className = "muted";
  state.textContent = pushLabel(row);
  const remark = document.createElement("input");
  remark.type = "text";
  remark.value = row.remark || "";
  remark.maxLength = 40;
  const enabled = document.createElement("input");
  enabled.type = "checkbox";
  enabled.checked = Boolean(row.enabled);
  const enabledLabel = document.createElement("label");
  enabledLabel.className = "check";
  enabledLabel.appendChild(enabled);
  enabledLabel.appendChild(document.createTextNode("开启推送"));
  const save = document.createElement("button");
  save.type = "button";
  save.textContent = "保存";
  save.addEventListener("click", () => {
    saveRow(row.group_id, remark.value, enabled.checked);
  });
  const remove = document.createElement("button");
  remove.type = "button";
  remove.textContent = "删除";
  remove.addEventListener("click", () => {
    removeRow(row.group_id);
  });
  box.appendChild(title);
  box.appendChild(state);
  box.appendChild(remark);
  box.appendChild(enabledLabel);
  box.appendChild(save);
  box.appendChild(remove);
  return box;
}

async function loadGroups() {
  // 向页面接口拉当前群表。
  const result = await bridge.apiGet("groups");
  const groups = result && result.groups ? result.groups : [];
  renderGroups(groups);
}

async function loadStatus() {
  // 向页面接口拉最近一轮轮询，不额外打来源。
  const result = await bridge.apiGet("status");
  statusBox.textContent = formatStatus(result || {});
}

function formatStatus(result) {
  // 把轮询状态收成几行字。还没基线时不要把空 id 说成已在监控。
  const lines = [];
  if (!result.baselined) {
    lines.push("还没有基线。第一次成功拉取只记位置，不推历史重置。");
  }
  lines.push("上次见到的事件：" + (result.last_seen_id || "无"));
  lines.push("上次重置时间：" + (result.last_reset_at || "无"));
  lines.push("最近一轮：" + (result.last_poll_at || "还没轮询"));
  lines.push("最近一轮错误：" + (result.last_error || "无"));
  lines.push("最近一轮推送条数：" + String(result.last_message_count || 0));
  lines.push(result.source_label || "Data: codex-reset.com");
  lines.push(result.source_url || "https://codex-reset.com");
  return lines.join("\n");
}

function showNotice(result) {
  // 通知没发出去时留在页面上，避免用户以为群里已经看到了。
  const notice = result && result.notice ? String(result.notice) : "";
  if (!notice) {
    return;
  }
  showFormError(notice);
}


async function addGroup() {
  // 提交新增。失败只显示原因，不刷新成成功。
  showFormError("");
  try {
    const result = await bridge.apiPost("groups", {
      group_id: fieldValue(groupIdInput),
      remark: fieldValue(remarkInput),
      enabled: Boolean(enabledInput && enabledInput.checked),
    });
    groupIdInput.value = "";
    remarkInput.value = "";
    await loadGroups();
    showNotice(result);
  } catch (error) {
    showFormError(errorText(error));
  }
}

async function saveRow(groupId, remark, enabled) {
  // 保存这一行的备注和开关。群号不变。
  showFormError("");
  try {
    const result = await bridge.apiPost("groups/update", {
      group_id: groupId,
      remark: String(remark || "").trim(),
      enabled: Boolean(enabled),
    });
    await loadGroups();
    showNotice(result);
  } catch (error) {
    showFormError(errorText(error));
  }
}

async function removeRow(groupId) {
  // 删除这一群。删掉后不再推送。
  showFormError("");
  try {
    await bridge.apiPost("groups/delete", { group_id: groupId });
    await loadGroups();
  } catch (error) {
    showFormError(errorText(error));
  }
}

function errorText(error) {
  // bridge 失败时尽量把后端原因显示出来。
  if (error && error.message) {
    return error.message;
  }
  return String(error);
}

async function refreshAll() {
  // 同时刷新群表和轮询状态。
  showFormError("");
  try {
    await loadGroups();
    await loadStatus();
  } catch (error) {
    showFormError(errorText(error));
  }
}

async function boot() {
  // module 脚本会等 bridge SDK。这里再挡一次，避免页面空白没说明。
  if (!bridge) {
    groupsBox.textContent = "页面桥接未就绪，请刷新后重试。";
    return;
  }
  await bridge.ready();
  addButton.addEventListener("click", () => {
    addGroup();
  });
  refreshButton.addEventListener("click", () => {
    refreshAll();
  });
  await refreshAll();
}

boot();
