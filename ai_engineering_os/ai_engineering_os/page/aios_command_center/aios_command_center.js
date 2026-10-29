frappe.pages["aios-command-center"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "AI Engineering OS Command Center",
    single_column: true,
  });

  const body = $(`
    <div class="aios-command-center" style="max-width: 960px;">
      <p class="text-muted">
        Preview-only planning and export actions. Skills remain inactive and no global Codex or Claude export is performed.
      </p>
      <div class="frappe-card" style="padding: 16px; margin-bottom: 12px;">
        <h4>Actions</h4>
        <ul>
          <li>Plan Request</li>
          <li>Export Codex Task Preview</li>
          <li>Export Claude Task Preview</li>
          <li>View Canonical Pack Preview</li>
        </ul>
      </div>
      <pre class="text-muted">Use System Manager-only API methods under ai_engineering_os.api.command_center.</pre>
    </div>
  `);
  $(page.body).append(body);
};
