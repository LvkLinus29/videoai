const imageInput = document.querySelector("#imageInput");
const audioInput = document.querySelector("#audioInput");
const imageDrop = document.querySelector("#imageDrop");
const audioDrop = document.querySelector("#audioDrop");
const imageList = document.querySelector("#imageList");
const audioName = document.querySelector("#audioName");
const audioPlayer = document.querySelector("#audioPlayer");
const videoPreview = document.querySelector("#videoPreview");
const previewPanel = document.querySelector("#previewPanel");
const renderButton = document.querySelector("#renderButton");
const settingsButton = document.querySelector("#settingsButton");
const aboutButton = document.querySelector("#aboutButton");
const statusEl = document.querySelector("#status");
const renderTime = document.querySelector("#renderTime");
const progressBar = document.querySelector("#progressBar");
const downloadLink = document.querySelector("#downloadLink");
const settingsModal = document.querySelector("#settingsModal");
const aboutModal = document.querySelector("#aboutModal");
const saveSettingsButton = document.querySelector("#saveSettingsButton");
const appVersion = document.querySelector("#appVersion");

let images = [];
let audio = null;
let draggedIndex = null;
let settings = {};

function setStatus(message) {
  statusEl.textContent = message;
}

function setProgress(percent) {
  progressBar.style.width = `${Math.max(0, Math.min(100, percent))}%`;
}

function formatSeconds(seconds) {
  if (seconds === null || seconds === undefined) return "";
  const value = Math.max(0, Number(seconds) || 0);
  if (value < 60) return `${value.toFixed(1)} s`;
  const minutes = Math.floor(value / 60);
  const rest = Math.round(value % 60).toString().padStart(2, "0");
  return `${minutes}:${rest} min`;
}

function setRenderTime(seconds) {
  renderTime.textContent = seconds === null || seconds === undefined ? "" : `Renderzeit: ${formatSeconds(seconds)}`;
}

function openModal(modal) {
  modal.classList.remove("hidden");
}

function closeModals() {
  document.querySelectorAll(".modal").forEach((modal) => modal.classList.add("hidden"));
}

function applyTheme(theme) {
  document.body.dataset.theme = theme === "light" ? "light" : "dark";
}

function fillSettingsForm(nextSettings) {
  document.querySelector("#settingTheme").value = nextSettings.theme || "dark";
  document.querySelector("#settingLanguage").value = nextSettings.language || "de";
  document.querySelector("#settingFormat").value = nextSettings.default_format || "mp4";
  document.querySelector("#settingResolution").value = nextSettings.default_resolution || "1920:1080";
  document.querySelector("#settingFps").value = nextSettings.default_fps || 30;
  document.querySelector("#settingFfmpeg").value = nextSettings.ffmpeg_path || "";
  document.querySelector("#settingOutputDir").value = nextSettings.default_output_dir || "";
}

function readSettingsForm() {
  return {
    theme: document.querySelector("#settingTheme").value,
    language: document.querySelector("#settingLanguage").value,
    default_format: document.querySelector("#settingFormat").value,
    default_resolution: document.querySelector("#settingResolution").value,
    default_fps: Number(document.querySelector("#settingFps").value || 30),
    ffmpeg_path: document.querySelector("#settingFfmpeg").value,
    default_output_dir: document.querySelector("#settingOutputDir").value,
  };
}

function applySettingsDefaults(nextSettings) {
  document.querySelector("#format").value = nextSettings.default_format || "mp4";
  document.querySelector("#resolution").value = nextSettings.default_resolution || "1920:1080";
  document.querySelector("#fps").value = nextSettings.default_fps || 30;
}

async function loadAppSettings() {
  const response = await fetch("/api/settings");
  const data = await response.json();
  if (!data.ok) throw new Error(data.error || "Einstellungen konnten nicht geladen werden.");
  settings = data.settings || {};
  if (data.version) appVersion.textContent = data.version;
  applyTheme(settings.theme);
  applySettingsDefaults(settings);
  fillSettingsForm(settings);
}

async function saveAppSettings() {
  const response = await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(readSettingsForm()),
  });
  const data = await response.json();
  if (!data.ok) throw new Error(data.error || "Einstellungen konnten nicht gespeichert werden.");
  settings = data.settings || {};
  applyTheme(settings.theme);
  applySettingsDefaults(settings);
  fillSettingsForm(settings);
  closeModals();
  setStatus("Einstellungen gespeichert.");
}

function revokeObjectUrls() {
  images.forEach((item) => URL.revokeObjectURL(item.url));
}

function renderFiles() {
  imageList.innerHTML = "";
  images.forEach((item, index) => {
    const tile = document.createElement("article");
    tile.className = "thumb";
    tile.draggable = true;
    tile.dataset.index = index;

    const image = document.createElement("img");
    image.src = item.url;
    image.alt = item.file.name;

    const footer = document.createElement("div");
    footer.className = "thumb-footer";

    const name = document.createElement("span");
    name.textContent = item.file.name;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "icon-button";
    remove.title = "Bild entfernen";
    remove.textContent = "×";
    remove.addEventListener("click", () => {
      URL.revokeObjectURL(item.url);
      images.splice(index, 1);
      renderFiles();
    });

    footer.append(name, remove);
    tile.append(image, footer);
    imageList.appendChild(tile);
  });

  audioName.textContent = audio ? audio.name : "Keine Audiodatei gewählt";
  if (audio) {
    audioPlayer.src = URL.createObjectURL(audio);
    audioPlayer.classList.remove("hidden");
  } else {
    audioPlayer.removeAttribute("src");
    audioPlayer.classList.add("hidden");
  }
}

function addImages(fileList) {
  const incoming = Array.from(fileList)
    .filter((file) => file.type.startsWith("image/"))
    .map((file) => ({ file, url: URL.createObjectURL(file) }));
  images = [...images, ...incoming];
  renderFiles();
}

function setAudio(fileList) {
  const incoming = Array.from(fileList).find((file) => file.type.startsWith("audio/"));
  if (incoming) {
    if (audioPlayer.src) {
      URL.revokeObjectURL(audioPlayer.src);
    }
    audio = incoming;
  }
  renderFiles();
}

function bindDrop(zone, onFiles) {
  zone.addEventListener("dragover", (event) => {
    event.preventDefault();
    zone.classList.add("dragover");
  });
  zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
  zone.addEventListener("drop", (event) => {
    event.preventDefault();
    zone.classList.remove("dragover");
    onFiles(event.dataTransfer.files);
  });
}

imageList.addEventListener("dragstart", (event) => {
  const tile = event.target.closest(".thumb");
  if (!tile) return;
  draggedIndex = Number(tile.dataset.index);
  tile.classList.add("dragging");
});

imageList.addEventListener("dragend", () => {
  draggedIndex = null;
  document.querySelectorAll(".thumb.dragging").forEach((tile) => tile.classList.remove("dragging"));
});

imageList.addEventListener("dragover", (event) => {
  event.preventDefault();
  const tile = event.target.closest(".thumb");
  if (!tile || draggedIndex === null) return;
  const targetIndex = Number(tile.dataset.index);
  if (targetIndex === draggedIndex) return;
  const [moved] = images.splice(draggedIndex, 1);
  images.splice(targetIndex, 0, moved);
  draggedIndex = targetIndex;
  renderFiles();
});

async function pollJob(jobId) {
  const response = await fetch(`/api/status/${jobId}`);
  const data = await response.json();
  if (!data.ok) {
    throw new Error(data.error || "Status konnte nicht geladen werden.");
  }

  setProgress(data.progress || 0);
  setStatus(data.message || "Rendering...");
  setRenderTime(data.elapsed_seconds);

  if (data.status === "done") {
    downloadLink.href = data.download;
    downloadLink.download = data.filename;
    downloadLink.classList.remove("hidden");
    videoPreview.src = data.download;
    previewPanel.classList.remove("hidden");
    setStatus(`Fertig: ${data.path}`);
    setRenderTime(data.elapsed_seconds);
    return;
  }

  if (data.status === "error") {
    throw new Error(data.error || data.message || "Rendern fehlgeschlagen.");
  }

  setTimeout(() => pollJob(jobId).catch(showError), 700);
}

function showError(error) {
  setStatus(error.message);
  renderButton.disabled = false;
}

imageInput.addEventListener("change", () => addImages(imageInput.files));
audioInput.addEventListener("change", () => setAudio(audioInput.files));
bindDrop(imageDrop, addImages);
bindDrop(audioDrop, setAudio);
settingsButton.addEventListener("click", () => openModal(settingsModal));
aboutButton.addEventListener("click", () => openModal(aboutModal));
document.querySelectorAll("[data-close-modal]").forEach((button) => button.addEventListener("click", closeModals));
document.querySelectorAll(".modal").forEach((modal) => {
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeModals();
  });
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeModals();
});
saveSettingsButton.addEventListener("click", () => saveAppSettings().catch(showError));

renderButton.addEventListener("click", async () => {
  if (!images.length) {
    setStatus("Bitte zuerst Fotos hinzufügen.");
    return;
  }
  if (!audio) {
    setStatus("Bitte zuerst eine Audiodatei hinzufügen.");
    return;
  }

  const form = new FormData();
  images.forEach((item) => form.append("images", item.file));
  form.append("audio", audio);
  form.append("format", document.querySelector("#format").value);
  form.append("resolution", document.querySelector("#resolution").value);
  form.append("fps", document.querySelector("#fps").value);
  form.append("seconds_per_image", document.querySelector("#seconds").value);

  renderButton.disabled = true;
  downloadLink.classList.add("hidden");
  previewPanel.classList.add("hidden");
  videoPreview.removeAttribute("src");
  setProgress(0);
  setRenderTime(null);
  setStatus("Upload läuft ...");

  try {
    const response = await fetch("/api/render", {
      method: "POST",
      body: form,
    });
    const data = await response.json();
    if (!data.ok) {
      throw new Error(data.error || "Rendern fehlgeschlagen.");
    }
    pollJob(data.job_id).catch(showError);
  } catch (error) {
    showError(error);
  }
});

window.addEventListener("beforeunload", revokeObjectUrls);
loadAppSettings().catch(showError);
renderFiles();
