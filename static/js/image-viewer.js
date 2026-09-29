/**
 * ImageViewer - zoom and pan for images inside a Bootstrap modal
 * Pointer Events based, no dependencies
 */

(function () {
    'use strict';

    const MIN_SCALE = 1;
    const MAX_SCALE = 5;
    const DOUBLE_TAP_SCALE = 2.5;
    const DOUBLE_TAP_DELAY = 300;
    const DOUBLE_TAP_DISTANCE = 30;
    const DRAG_THRESHOLD = 5;
    const WHEEL_STEP = 1.15;
    // Backdrop clicks right after a gesture are ignored: on touch devices the
    // browser emulates mousedown/click at the last touch point, which may land
    // outside the dialog and would close the modal in the middle of a zoom.
    const GESTURE_GRACE = 400;

    class ImageViewer {
        constructor(modalElement) {
            this.modal = modalElement;
            this.stage = modalElement.querySelector('.image-viewer-stage');
            this.img = modalElement.querySelector('.image-viewer-img');

            if (!this.stage || !this.img) {
                console.error('ImageViewer: stage or image not found');
                return;
            }

            this.scale = 1;
            this.tx = 0;
            this.ty = 0;
            this.baseW = 0;
            this.baseH = 0;
            this.pointers = new Map();
            this.mode = null;
            this.start = null;
            this.pinch = null;
            this.moved = false;
            this.gestureEndedAt = 0;
            this.lastTap = { time: 0, x: 0, y: 0 };
            this.animationTimer = null;

            this.bindEvents();
        }

        /** Show an image and reset the view to its initial state. */
        open(src, alt) {
            this.img.src = src;
            this.img.alt = alt || '';
            this.reset(false);

            if (this.img.complete) {
                this.measure();
            } else {
                this.img.addEventListener(
                    'load', () => this.measure(), { once: true }
                );
            }
        }

        /** Measure the fitted image size so panning can be clamped. */
        measure() {
            const cw = this.stage.clientWidth;
            const ch = this.stage.clientHeight;
            const nw = this.img.naturalWidth;
            const nh = this.img.naturalHeight;

            if (!nw || !nh || !cw || !ch) {
                this.baseW = cw;
                this.baseH = ch;
            } else {
                const ratio = Math.min(cw / nw, ch / nh);
                this.baseW = nw * ratio;
                this.baseH = nh * ratio;
            }

            this.clamp();
            this.apply();
        }

        bindEvents() {
            this.stage.addEventListener(
                'pointerdown', (e) => this.onPointerDown(e)
            );
            this.stage.addEventListener(
                'pointermove', (e) => this.onPointerMove(e)
            );
            this.stage.addEventListener(
                'pointerup', (e) => this.onPointerUp(e)
            );
            this.stage.addEventListener(
                'pointercancel', (e) => this.onPointerUp(e)
            );
            this.stage.addEventListener('click', (e) => this.onClick(e));
            this.stage.addEventListener(
                'wheel', (e) => this.onWheel(e), { passive: false }
            );
            // iOS Safari ignores touch-action for some gestures, so block the
            // native panning as a fallback.
            this.stage.addEventListener(
                'touchmove', (e) => e.preventDefault(), { passive: false }
            );

            this.modal.querySelectorAll('[data-zoom-in]').forEach((btn) => {
                btn.addEventListener(
                    'click', () => this.zoomBy(WHEEL_STEP * WHEEL_STEP)
                );
            });
            this.modal.querySelectorAll('[data-zoom-out]').forEach((btn) => {
                btn.addEventListener(
                    'click', () => this.zoomBy(1 / (WHEEL_STEP * WHEEL_STEP))
                );
            });
            this.modal.querySelectorAll('[data-zoom-reset]').forEach((btn) => {
                btn.addEventListener('click', () => this.reset(true));
            });

            this.modal.addEventListener('shown.bs.modal', () => this.measure());
            this.modal.addEventListener('hidden.bs.modal', () => this.reset(false));

            window.addEventListener('resize', () => this.measure());

            // Runs before Bootstrap's own mousedown handler on the modal element
            document.addEventListener(
                'mousedown', (e) => this.onBackdropMouseDown(e), true
            );
        }

        onBackdropMouseDown(e) {
            if (e.target !== this.modal) return;
            if (Date.now() - this.gestureEndedAt > GESTURE_GRACE) return;
            this.gestureEndedAt = 0;
            e.stopPropagation();
            e.preventDefault();
        }

        isControl(target) {
            if (!target.closest) return false;
            return !!target.closest(
                '.image-viewer-controls, .btn-close'
            );
        }

        onPointerDown(e) {
            if (this.isControl(e.target)) return;

            this.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
            if (this.stage.setPointerCapture) {
                // Capture may fail when the pointer is already gone
                try {
                    this.stage.setPointerCapture(e.pointerId);
                } catch (err) {
                    // Panning still works through the stage listeners
                }
            }

            if (this.pointers.size === 1) {
                this.mode = 'pan';
                this.start = {
                    x: e.clientX, y: e.clientY, tx: this.tx, ty: this.ty,
                };
                this.moved = false;
            } else if (this.pointers.size === 2) {
                const [a, b] = Array.from(this.pointers.values());
                this.mode = 'pinch';
                this.moved = true;
                this.pinch = {
                    distance: Math.hypot(a.x - b.x, a.y - b.y),
                    centerX: (a.x + b.x) / 2,
                    centerY: (a.y + b.y) / 2,
                    scale: this.scale,
                    tx: this.tx,
                    ty: this.ty,
                };
            }
        }

        onPointerMove(e) {
            if (!this.pointers.has(e.pointerId)) return;

            this.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });

            if (this.mode === 'pinch' && this.pointers.size >= 2) {
                this.updatePinch();
            } else if (this.mode === 'pan' && this.pointers.size === 1) {
                const dx = e.clientX - this.start.x;
                const dy = e.clientY - this.start.y;

                if (Math.abs(dx) > DRAG_THRESHOLD
                    || Math.abs(dy) > DRAG_THRESHOLD) {
                    this.moved = true;
                    this.stage.classList.add('is-dragging');
                }

                this.tx = this.start.tx + dx;
                this.ty = this.start.ty + dy;
                this.clamp();
                this.apply();
            }
        }

        updatePinch() {
            const [a, b] = Array.from(this.pointers.values());
            const distance = Math.hypot(a.x - b.x, a.y - b.y);
            const centerX = (a.x + b.x) / 2;
            const centerY = (a.y + b.y) / 2;

            if (!this.pinch.distance) return;

            const scale = this.clampScale(
                this.pinch.scale * (distance / this.pinch.distance)
            );
            const origin = this.toLocal(
                this.pinch.centerX, this.pinch.centerY
            );
            // Image point that must stay under the pinch center
            const px = (origin.x - this.pinch.tx) / this.pinch.scale;
            const py = (origin.y - this.pinch.ty) / this.pinch.scale;
            const current = this.toLocal(centerX, centerY);

            this.scale = scale;
            this.tx = current.x - px * scale;
            this.ty = current.y - py * scale;
            this.clamp();
            this.apply();
        }

        onPointerUp(e) {
            if (!this.pointers.has(e.pointerId)) return;

            this.pointers.delete(e.pointerId);
            this.stage.classList.remove('is-dragging');

            if (this.pointers.size === 0) {
                if (this.moved) {
                    this.gestureEndedAt = Date.now();
                }
                this.mode = null;
                this.start = null;
                this.pinch = null;
            } else if (this.pointers.size === 1) {
                // A pinch turned into a one-finger drag
                const [p] = Array.from(this.pointers.values());
                this.mode = 'pan';
                this.start = { x: p.x, y: p.y, tx: this.tx, ty: this.ty };
            }
        }

        onClick(e) {
            if (this.isControl(e.target)) return;

            if (this.moved) {
                this.moved = false;
                return;
            }

            const now = Date.now();
            const nearLast = (
                Math.abs(e.clientX - this.lastTap.x) < DOUBLE_TAP_DISTANCE
                && Math.abs(e.clientY - this.lastTap.y) < DOUBLE_TAP_DISTANCE
            );

            if (now - this.lastTap.time < DOUBLE_TAP_DELAY && nearLast) {
                this.lastTap.time = 0;
                if (this.scale > MIN_SCALE + 0.01) {
                    this.reset(true);
                } else {
                    this.zoomTo(e.clientX, e.clientY, DOUBLE_TAP_SCALE);
                }
                return;
            }

            this.lastTap = { time: now, x: e.clientX, y: e.clientY };
        }

        onWheel(e) {
            e.preventDefault();
            const factor = e.deltaY < 0 ? WHEEL_STEP : 1 / WHEEL_STEP;
            // No easing here: wheel events come in bursts and the animation
            // would lag behind the cursor
            this.zoomTo(e.clientX, e.clientY, this.scale * factor, false);
        }

        /** Zoom around a screen point, keeping it visually in place. */
        zoomTo(clientX, clientY, targetScale, animate = true) {
            const scale = this.clampScale(targetScale);
            const origin = this.toLocal(clientX, clientY);
            const px = (origin.x - this.tx) / this.scale;
            const py = (origin.y - this.ty) / this.scale;

            this.scale = scale;
            this.tx = origin.x - px * scale;
            this.ty = origin.y - py * scale;
            this.clamp();

            if (animate) {
                this.animate();
            } else {
                this.apply();
            }
        }

        /** Zoom around the center of the stage (used by the buttons). */
        zoomBy(factor) {
            const rect = this.stage.getBoundingClientRect();
            this.zoomTo(
                rect.left + rect.width / 2,
                rect.top + rect.height / 2,
                this.scale * factor
            );
        }

        reset(animate) {
            this.scale = MIN_SCALE;
            this.tx = 0;
            this.ty = 0;
            this.pointers.clear();
            this.mode = null;
            this.start = null;
            this.pinch = null;
            this.moved = false;
            this.stage.classList.remove('is-dragging');

            if (animate) {
                this.animate();
            } else {
                this.apply();
            }
        }

        clampScale(scale) {
            return Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale));
        }

        clamp() {
            const maxX = Math.max(
                0, (this.baseW * this.scale - this.stage.clientWidth) / 2
            );
            const maxY = Math.max(
                0, (this.baseH * this.scale - this.stage.clientHeight) / 2
            );

            this.tx = Math.min(maxX, Math.max(-maxX, this.tx));
            this.ty = Math.min(maxY, Math.max(-maxY, this.ty));
        }

        /** Convert screen coordinates to stage-center coordinates. */
        toLocal(clientX, clientY) {
            const rect = this.stage.getBoundingClientRect();
            return {
                x: clientX - rect.left - rect.width / 2,
                y: clientY - rect.top - rect.height / 2,
            };
        }

        apply() {
            this.img.style.transform = (
                `translate3d(${this.tx}px, ${this.ty}px, 0) ` +
                `scale(${this.scale})`
            );
        }

        animate() {
            this.stage.classList.add('is-animated');
            this.apply();
            clearTimeout(this.animationTimer);
            this.animationTimer = setTimeout(() => {
                this.stage.classList.remove('is-animated');
            }, 220);
        }
    }

    // Export for use in templates
    window.ImageViewer = ImageViewer;
})();