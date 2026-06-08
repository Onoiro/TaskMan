/**
 * MarkdownToolbar - lightweight component for Markdown formatting
 * No dependencies, works with Bootstrap Icons
 */

class MarkdownToolbar {
    constructor(textareaId, previewId, options = {}) {
        this.textarea = document.getElementById(textareaId);
        this.preview = previewId ? document.getElementById(previewId) : null;
        this.options = {
            uploadUrl: options.uploadUrl || null,
            ...options
        };

        if (!this.textarea) {
            console.error('MarkdownToolbar: textarea not found');
            return;
        }

        this.buttons = [
            { id: 'bold', icon: 'bi-type-bold', title: 'Bold', syntax: { before: '**', after: '**' } },
            { id: 'italic', icon: 'bi-type-italic', title: 'Italic', syntax: { before: '*', after: '*' } },
            { id: 'heading', icon: 'bi-type-h1', title: 'Heading', syntax: { before: '## ', after: '' } },
            { id: 'quote', icon: 'bi-quote', title: 'Quote', syntax: { before: '> ', after: '' } },
            { id: 'code', icon: 'bi-code-slash', title: 'Code', syntax: { before: '```\n', after: '\n```' } },
            { id: 'link', icon: 'bi-link-45deg', title: 'Link', syntax: { before: '[', after: '](url)' } },
            { id: 'image', icon: 'bi-image', title: 'Image', action: 'image' },
            { id: 'ul', icon: 'bi-list-ul', title: 'Unordered List', syntax: { before: '- ', after: '' } },
            { id: 'ol', icon: 'bi-list-ol', title: 'Ordered List', syntax: { before: '1. ', after: '' } },
            { id: 'table', icon: 'bi-table', title: 'Table', action: 'table' },
            { id: 'preview', icon: 'bi-eye', title: 'Preview', action: 'togglePreview' }
        ];

        this.init();
    }

    init() {
        this.renderToolbar();
        this.attachEvents();
    }

    renderToolbar() {
        const toolbar = document.createElement('div');
        toolbar.className = 'markdown-toolbar btn-group flex-nowrap overflow-auto mb-2';
        toolbar.setAttribute('role', 'toolbar');

        this.buttons.forEach(btn => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'btn btn-outline-secondary btn-sm markdown-toolbar-btn';
            button.setAttribute('data-action', btn.id);
            button.setAttribute('title', btn.title);
            button.innerHTML = `<i class="bi ${btn.icon}"></i>`;
            toolbar.appendChild(button);
        });

        // Insert toolbar before editor-col (which contains the textarea)
        const editorContainer = document.getElementById('markdown-editor-container');
        if (editorContainer) {
            const editorCol = this.textarea.closest('.editor-col');
            if (editorCol) {
                editorContainer.insertBefore(toolbar, editorCol);
            } else {
                editorContainer.insertBefore(toolbar, this.textarea);
            }
        } else {
            this.textarea.parentNode.insertBefore(toolbar, this.textarea);
        }
        this.toolbarElement = toolbar;
    }

    attachEvents() {
        this.toolbarElement.addEventListener('click', (e) => {
            const btn = e.target.closest('button');
            if (!btn) return;

            const action = btn.getAttribute('data-action');
            const buttonConfig = this.buttons.find(b => b.id === action);

            if (buttonConfig) {
                e.preventDefault();
                this.handleAction(buttonConfig);
            }
        });

        // Live preview on input
        if (this.preview) {
            this.textarea.addEventListener('input', () => this.updatePreview());
        }
    }

    handleAction(buttonConfig) {
        if (buttonConfig.action) {
            this[buttonConfig.action]();
        } else if (buttonConfig.syntax) {
            this.insertText(buttonConfig.syntax.before, buttonConfig.syntax.after);
        }
    }

    insertText(before, after = '') {
        const textarea = this.textarea;
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const selectedText = textarea.value.substring(start, end);
        const text = textarea.value;

        // Insert syntax
        const newText = text.substring(0, start) + before + selectedText + after + text.substring(end);
        textarea.value = newText;

        // Restore focus and cursor position
        textarea.focus();
        if (selectedText) {
            textarea.setSelectionRange(start + before.length, end + before.length);
        } else {
            const cursorPos = start + before.length;
            textarea.setSelectionRange(cursorPos, cursorPos);
        }

        // Update preview
        if (this.preview) {
            this.updatePreview();
        }

        // Trigger change event for Django form
        textarea.dispatchEvent(new Event('change', { bubbles: true }));
    }

    image() {
        // Open modal for image insertion
        const modal = document.getElementById('imageModal');
        if (modal) {
            const modalInstance = new bootstrap.Modal(modal);
            modalInstance.show();

            // Insert handler
            const insertBtn = modal.querySelector('[data-insert-image]');
            if (insertBtn) {
                insertBtn.onclick = () => {
                    const url = modal.querySelector('#imageUrl').value.trim();
                    const alt = modal.querySelector('#imageAlt').value.trim() || 'Image';

                    if (url) {
                        this.insertText(`![${alt}](`, `)`);
                        // Insert URL between parentheses
                        const start = this.textarea.selectionStart;
                        const text = this.textarea.value;
                        const newText = text.substring(0, start - 1) + url + text.substring(start - 1);
                        this.textarea.value = newText;
                        this.textarea.focus();
                        this.textarea.setSelectionRange(start - 1, start - 1);
                    }

                    modalInstance.hide();
                };
            }
        }
    }

    table() {
        const tableTemplate = `
| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |
`;
        this.insertText(tableTemplate, '');
    }

    togglePreview() {
        if (!this.preview) return;

        const previewCol = this.preview.closest('.preview-col');
        const editorCol = this.textarea.closest('.editor-col');

        if (previewCol.classList.contains('d-none')) {
            // Show preview
            previewCol.classList.remove('d-none');
            editorCol.classList.remove('flex-grow-1');
            editorCol.classList.add('flex-grow-1');
            this.updatePreview();

            // Update icon
            const previewBtn = this.toolbarElement.querySelector('[data-action="preview"]');
            if (previewBtn) {
                previewBtn.innerHTML = '<i class="bi bi-eye-slash"></i>';
                previewBtn.setAttribute('title', 'Hide Preview');
            }
        } else {
            // Hide preview
            previewCol.classList.add('d-none');

            // Update icon
            const previewBtn = this.toolbarElement.querySelector('[data-action="preview"]');
            if (previewBtn) {
                previewBtn.innerHTML = '<i class="bi bi-eye"></i>';
                previewBtn.setAttribute('title', 'Preview');
            }
        }
    }

    updatePreview() {
        if (!this.preview) return;

        const markdownText = this.textarea.value;

        if (typeof marked !== 'undefined') {
            const html = marked.parse(markdownText);
            this.preview.innerHTML = html;

            // Apply syntax highlighting
            if (typeof hljs !== 'undefined') {
                this.preview.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightElement(block);
                });
            }
        } else {
            // Fallback: plain text
            this.preview.textContent = markdownText;
        }
    }
}

// Export for use in templates
window.MarkdownToolbar = MarkdownToolbar;
