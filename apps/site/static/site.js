
(() => {
  "use strict";

  const resetCopyButtonLabel = (button, defaultLabel) => {
    setTimeout(() => {
      button.textContent = defaultLabel;
    }, 1600);
  };

  document.querySelectorAll(".copy-button[data-copy-text]").forEach((button) => {
    button.addEventListener("click", async () => {
      const defaultLabel = button.dataset.copyDefault || "Copy command";
      const command = button.dataset.copyText;
      if (!command) {
        return;
      }
      try {
        await navigator.clipboard.writeText(command);
        button.textContent = "Copied";
      } catch {
        button.textContent = "Copy manually";
      }
      resetCopyButtonLabel(button, defaultLabel);
    });
  });

  const publishForm = document.getElementById("publish-goal-form");
  if (!publishForm) {
    return;
  }
  const resultPanel = document.getElementById("publish-result");
  const resultSummary = document.getElementById("publish-result-summary");
  const resultCommand = document.getElementById("publish-result-command");
  const resultGoalLink = document.getElementById("publish-result-goal-link");
  const resultJoinLink = document.getElementById("publish-result-join-link");

  publishForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(publishForm);
    const payload = {
      title: formData.get("title"),
      summary: formData.get("summary"),
      objective: formData.get("objective"),
      metric_name: formData.get("metric_name"),
      direction: formData.get("direction"),
      platform: formData.get("platform"),
      budget_seconds: Number(formData.get("budget_seconds")),
      actor_id: formData.get("actor_id"),
      constraints: String(formData.get("constraints") || "").split("\n").map((line) => line.trim()).filter(Boolean),
      evidence_requirement: formData.get("evidence_requirement"),
      stop_condition: formData.get("stop_condition"),
    };

    const response = await fetch("/publish", {
      method: "POST",
      headers: {"content-type": "application/json"},
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok) {
      alert(body.detail || "Could not publish goal.");
      return;
    }

    resultPanel.hidden = false;
    resultSummary.textContent = `Published ${payload.title}. The live goal page is ready and the join command is attached.`;
    resultCommand.textContent = body.join_command;
    resultGoalLink.href = body.goal_page_url;
    resultJoinLink.onclick = async (clickEvent) => {
      clickEvent.preventDefault();
      await navigator.clipboard.writeText(body.join_command);
      resultJoinLink.textContent = "Copied join command";
      resetCopyButtonLabel(resultJoinLink, "Copy join command");
    };
    window.location = body.goal_page_url;
  });
})();
