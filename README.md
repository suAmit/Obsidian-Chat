# 🧠 Obsidian Chat (Local RAG MVP)

A Retrieval-Augmented Generation (RAG) system that connects your local Obsidian Vault to a lightweight LLM. Built with Python (FastAPI + ChromaDB) and a custom JavaScript Sidebar for Obsidian.

---

## 📂 Project Structure

```text
Local-RAG/
├── obsidian plugin/    # Frontend: Obsidian JS Plugin
│   ├── main.js
│   ├── manifest.json
│   └── styles.css
├── server/             # Backend: Python Package
│   ├── config.py       # Path & Model Configuration
│   ├── database.py     # ChromaDB Vector Store
│   ├── engine.py       # Hybrid Search & RAG Logic
│   ├── models.py       # Pydantic Schemas
│   └── processor.py    # Markdown Parsing & Chunking
├── main.py             # FastAPI Entry Point
├── README.md           # This guide
└── requirements.txt    # Python Dependencies

```

---

## 🛠️ Step 1: Backend Setup (Python 3.11.2)

1. **Environment Setup**:
   Navigate to the root directory and set up your environment using `pyenv`:

```bash
pyenv local 3.11.2
python -m venv venv
source venv/bin/activate

```

2. **Install Dependencies**:

```bash
pip install -r requirements.txt

```

3. **Vault Configuration**:
   Open `server/config.py` and ensure the `VAULT_PATH` points to your absolute vault location:

```python
# Example:
VAULT_PATH = "/home/user/Documents/MyVault"

```

---

## 🤖 Step 2: AI Model Setup (Ollama)

This project uses **Ollama** to run models locally on your CPU/GPU.

1. **Install Ollama**: Download from [ollama.com](https://ollama.com).
2. **Pull the Model**:

```bash
ollama pull llama3.2:1b

```

---

## 🔌 Step 3: Obsidian Plugin Installation (Visual Guide)

To make the "Second Brain" sidebar appear in Obsidian, you must move the plugin files into your Vault's internal configuration folder.

### 1. Prepare the Destination Folder

1. Open your **Obsidian Vault** folder in your File Manager (Thunar, Dolphin, etc.).
2. Show hidden files (Press **`Ctrl + H`**). You should now see a folder named `.obsidian`.
3. Go into `.obsidian` > `plugins`.
4. Create a new folder here named `obsidian-chat`.

### 2. Copy the Plugin Files

1. Open your **Project Folder** (`Local-RAG`) in a second window.
2. Open the folder named `obsidian plugin`.
3. Select these **3 files**: `main.js`, `manifest.json`, `styles.css`.
4. **Copy and Paste** these 3 files into the `obsidian-chat` folder you created in your Vault.

### 3. Activate in Obsidian

1. Open **Obsidian**.
2. Click **Settings** (Gear icon) > **Community Plugins**.
3. If **Restricted Mode** is ON, click **Turn off Restricted Mode**.
4. Click the **Refresh** button next to "Installed plugins".
5. Find **Obsidian Chat** in the list and click the **Toggle Switch** to turn it ON.

---

## 🚀 Step 4: Usage Workflow

Since this is a manual setup, follow these steps to start your "Obsidian Chat":

1. **Start the Server**:

```bash
source venv/bin/activate
python main.py

```

2. **Sync Your Notes**:
   In the Obsidian Sidebar, click the **Sync** button. This will parse your markdown files and store them in `chroma_db/`.
3. **Chat**:
   Type your questions in the sidebar. The system will retrieve relevant notes and answer using the local LLM.
4. **Shutdown**:
   Press `Ctrl+C` in your terminal to stop the backend when finished.

---

## ⚠️ Troubleshooting

- **Hidden Folders**: On Arch Linux, the `.obsidian` folder is hidden by default. Always press `Ctrl + H` in your file manager to find it.
- **Missing Documents**: If you add new notes, remember to hit **Sync** in the sidebar.
- **Connection Error**: Ensure `main.py` is running in a terminal before trying to chat in Obsidian.
