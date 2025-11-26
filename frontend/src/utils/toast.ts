export type ToastType = 'success' | 'error';

export function showToast(message: string, type: ToastType = 'success', duration = 3000) {
  const container = document.getElementById('toast-root');
  if (!container) return;
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerText = message;
  container.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(-5px)';
    setTimeout(() => container.removeChild(el), 200);
  }, duration);
}
