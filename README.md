# Photoshop-UI-Builder-Pro
A standalone No-Code visual node-based desktop application to design and generate Adobe Photoshop JSX UI scripts

Say goodbye to manually writing tedious UI code. This tool provides a **No-Code, drag-and-drop interface** with a dual-view architecture (Visual Canvas + Node System) to instantly design and export complex `.jsx` scripts. 

---

## 🚀 Download & Run (For Windows Users)
You do **not** need to install Python or any dependencies to use this software!

1. Go to the **[Releases](#)** tab of this repository. *(Add your release link here)*
2. Download the `PhotoshopGUI_Gen_NodeBase.exe` file.
3. Double-click the `.exe` file to launch the studio instantly.

*(Note: For developers who want to run or modify the Python source code, see the bottom of this page).*

---

## ✨ Comprehensive Feature List

### 🏗️ Advanced UI Canvas
* **Drag & Drop Workspace:** Add UI elements, resize them dynamically, and position them anywhere on a grid-snapped canvas.
* **Rich Element Library:** Includes Groups, Panels, Tabs, Buttons, Sliders, Dropdowns, Progress Bars, TreeViews, Image placeholders, and Layout Spacers.
* **Smart Parent Dragging:** Moving a parent container automatically moves all nested child elements inside it seamlessly.
* **Z-Index Management:** Easily bring elements forward or push them backward using the **Layer Up / Layer Down** controls in the properties panel.
* **Multi-Selection & Alignment:** Select multiple elements (Shift + Click) to align them (Left, Right, Center, Top, Bottom) or distribute spacing evenly (Horizontally/Vertically).

### 🧠 Node-Based Wiring System
* **Dual-View Architecture:** The bottom panel features a fully interactive Node Canvas to visualize your UI's hierarchy.
* **Visual Parenting:** Connect output/input sockets using cubic-bezier edge wiring to instantly set parent-child relationships between elements.
* **Middle-Mouse Panning:** Easily navigate complex UI node trees with smooth canvas panning.

### ⚡ Logic & Code Generation
* **Dynamic Event Binding:** Directly assign `onClick` or `onChange` events to your buttons and sliders right from the properties panel.
* **Custom JS Injection:** Write custom JavaScript logic inside the tool, which automatically gets injected into the final exported script.
* **Instant JSX Export:** One click compiles your entire visual layout, element properties, parent-child wiring, and custom logic into a production-ready Adobe Photoshop `.jsx` script.

### 💾 State & Project Management
* **Save/Load Projects:** Save your workspace state as a `.json` file and resume your work anytime.
* **30-Step Undo/Redo:** A robust memory stack ensures you never lose your progress during complex designing.

---

## ⌨️ Pro Shortcuts

Work faster with built-in keyboard shortcuts:

| Shortcut | Action |
| :--- | :--- |
| `Ctrl + S` | Quick Save |
| `Ctrl + Shift + S` | Save As... |
| `Ctrl + C` / `Ctrl + V` / `Ctrl + X` | Copy / Paste / Cut |
| `Ctrl + D` | Duplicate Selected |
| `Ctrl + Z` | Undo |
| `Ctrl + Y` (or `Ctrl+Shift+Z`) | Redo |
| `Shift + Click` | Multi-select Elements |
| `Delete` | Remove Selected |
| `Middle Mouse` | Pan Node Canvas |

---

## 👨‍💻 For Python Developers (Source Code)

If you want to modify the source code or run the raw script:

1. Clone the repository:
   ```bash
   git clone [https://github.com/earthlyakash/photoshop-ui-builder-pro.git](https://github.com/earthlyakash/photoshop-ui-builder-pro.git)

Developed by | Akash Kumar
📧 earthlyakash@gmail.com | Version 1.0.0
