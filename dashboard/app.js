const API = window.IG_API_BASE || "http://127.0.0.1:8000";

const $ = (id) => document.getElementById(id);
const request = async (path, options = {}) => {
  const response = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
};

function element(tag, text, className) {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  return node;
}

function renderCards(items) {
  const target = $("content-list");
  target.replaceChildren();
  if (!items.length) {
    target.append(element("p", "No content yet. Create a draft to begin."));
    return;
  }
  for (const item of items) {
    const card = element("article", "", "content-card");
    const heading = element("h3", `${item.campaign_name} · ${item.content_format}`);
    const meta = element("div", `${item.content_pillar} · ${item.approval_status}`, "content-meta");
    const caption = element("p", item.caption);
    const actions = element("div", "", "content-actions");
    if (item.approval_status === "pending") {
      const approve = element("button", "Approve draft");
      approve.type = "button";
      approve.addEventListener("click", () => decide(item.content_id, true));
      const reject = element("button", "Reject");
      reject.type = "button";
      reject.addEventListener("click", () => decide(item.content_id, false));
      actions.append(approve, reject);
    } else if (item.approval_status === "approved") {
      const schedule = element("button", "Schedule (mock)");
      schedule.type = "button";
      schedule.addEventListener("click", () => scheduleContent(item.content_id));
      actions.append(schedule);
    }
    card.append(heading, meta, caption);
    if (item.script) card.append(element("p", `Script: ${item.script}`));
    card.append(actions);
    target.append(card);
  }
}

async function decide(contentId, approved) {
  const reviewer = window.prompt("Enter the human reviewer's name:");
  if (!reviewer || !reviewer.trim()) return;
  try {
    await request(`/api/content/${contentId}/approval`, {
      method: "POST",
      body: JSON.stringify({ approved, approved_by: reviewer.trim() }),
    });
    await refresh();
  } catch (error) {
    $("notice").textContent = error.message;
  }
}

async function scheduleContent(contentId) {
  try {
    await request(`/api/content/${contentId}/schedule`, { method: "POST" });
    $("notice").textContent = "Mock schedule recorded; nothing was sent to Instagram.";
    await refresh();
  } catch (error) {
    $("notice").textContent = error.message;
  }
}

async function refresh() {
  try {
    const [items, analytics, activities, calendar] = await Promise.all([
      request("/api/content"),
      request("/api/analytics"),
      request("/api/activity"),
      request("/api/calendar"),
    ]);
    renderCards(items);
    $("metric-count").textContent = analytics.content_items;
    $("metric-pending").textContent = analytics.approval_counts.pending;
    $("metric-source").textContent = analytics.data_origin;
    $("activity").replaceChildren(...activities.flatMap((item) =>
      item.events.map((event) => element("p", `${item.content_id.slice(0, 8)} · ${event}`))));
    $("calendar").replaceChildren(...calendar.map((item) =>
      element("p", `${item.scheduled_publish_date || "No date"} · ${item.campaign_name} (${item.approval_status})`)));
  } catch (error) {
    $("notice").textContent = `API unavailable: ${error.message}`;
  }
}

$("draft-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const body = Object.fromEntries(form.entries());
  try {
    await request("/api/pipeline/run", { method: "POST", body: JSON.stringify(body) });
    $("notice").textContent = "Draft created and queued for your review.";
    event.currentTarget.reset();
    await refresh();
  } catch (error) {
    $("notice").textContent = error.message;
  }
});
$("refresh").addEventListener("click", refresh);
refresh();
