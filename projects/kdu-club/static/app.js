'use strict';
// UI 상태만 브라우저에서 관리합니다. 데이터 변경과 권한 검사는 서버에서 수행합니다.
const params = new URLSearchParams(location.search);
function setTab(group, name) {
  document.querySelectorAll(`[data-tab-group="${group}"] [data-tab]`).forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  document.querySelectorAll(`[data-panel-group="${group}"]`).forEach(p => p.hidden = !p.dataset.panel.split(' ').includes(name));
  if (group === 'notices') {
    const visible = [...document.querySelectorAll('.notification-row')].some(p => !p.hidden);
    document.querySelector('[data-notices-empty]').hidden = visible;
  }
}
document.querySelectorAll('[data-tab-group]').forEach(nav => {
  const group = nav.dataset.tabGroup;
  const choices = [...nav.querySelectorAll('[data-tab]')];
  const wanted = group === 'activity' ? params.get('tab') : null;
  setTab(group, choices.some(b => b.dataset.tab === wanted) ? wanted : choices[0].dataset.tab);
  choices.forEach(b => b.addEventListener('click', () => setTab(group, b.dataset.tab)));
});
document.querySelectorAll('[data-open-dialog]').forEach(b => b.addEventListener('click', () => document.getElementById(b.dataset.openDialog).showModal()));
document.querySelectorAll('[data-close-dialog]').forEach(b => b.addEventListener('click', () => b.closest('dialog').close()));
document.querySelectorAll('[data-auto-open]').forEach(d => d.showModal());
document.querySelectorAll('dialog').forEach(d => d.addEventListener('click', e => {if (e.target === d) {const r = d.getBoundingClientRect(); if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) d.close();}}));
document.querySelectorAll('[data-reject]').forEach(b => b.addEventListener('click', e => {
  const field = b.form.querySelector('[name="rejection_reason"]');
  if (!field.value.trim()) {e.preventDefault(); field.setCustomValidity('반려 사유를 입력해주세요.'); field.reportValidity(); field.focus();}
}));
document.querySelectorAll('[name="rejection_reason"]').forEach(f => f.addEventListener('input', () => f.setCustomValidity('')));
document.querySelectorAll('.section-tabs a').forEach(a => a.addEventListener('click', () => {document.querySelectorAll('.section-tabs a').forEach(b => b.classList.toggle('active',b === a));}));
// category 버튼을 눌렀을 때 이전 선택값이 중복 전송되지 않도록 합니다.
document.querySelector('.search-card')?.addEventListener('submit', e => {if (e.submitter?.name === 'category') document.querySelector('[data-category-hidden]')?.remove();});

const attachmentForm = document.querySelector('[data-attachment-form]');
if (attachmentForm) {
  const list = attachmentForm.querySelector('[data-attachments]');
  const picker = document.getElementById('attachment-picker');
  const errorBox = attachmentForm.querySelector('[data-upload-error]');
  const errorText = attachmentForm.querySelector('[data-upload-error-text]');
  const status = attachmentForm.querySelector('[data-upload-status]');
  const save = attachmentForm.querySelector('[data-save-post]');
  const dropzone = attachmentForm.querySelector('[data-dropzone]');
  let uploading = false;
  function showError(message) {errorText.textContent = message; errorBox.hidden = false;}
  list.addEventListener('click', e => {const b = e.target.closest('[data-remove-attachment]'); if (b && !uploading) b.closest('[data-attachment]').remove();});
  async function upload(files) {
    if (uploading) return;
    errorBox.hidden = true;
    uploading = true; save.disabled = true; picker.disabled = true;
    const errors = [];
    try {
      for (const file of files) {
        if (list.querySelectorAll('[data-attachment]').length >= 3) {errors.push(`${file.name}: 첨부파일은 최대 3개입니다.`); continue;}
        if (file.size > 10 * 1024 * 1024) {errors.push(`${file.name}: 파일당 최대 10MB입니다.`); continue;}
        status.textContent = `${file.name} 업로드 중…`;
        const body = new FormData(); body.append('file', file); body.append('csrf_token', document.querySelector('meta[name="csrf-token"]').content);
        try {
          const response = await fetch(attachmentForm.dataset.uploadUrl, {method:'POST',body});
          const result = await response.json();
          if (!response.ok) {errors.push(`${file.name}: ${result.error || '업로드를 완료하지 못했습니다.'}`); continue;}
          const row = document.createElement('div'); row.className = 'file-row'; row.dataset.attachment = result.id;
          const img = document.createElement('img'); img.src = '/static/icons/file-text.svg'; img.alt = ''; img.className = 'icon blue';
          const title = document.createElement('span'); title.className = 'file-title'; title.textContent = `${result.name} · ${(result.size/1024/1024).toFixed(1)} MB`;
          const hidden = document.createElement('input'); hidden.type = 'hidden'; hidden.name = 'attachment_ids'; hidden.value = result.id;
          const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'btn white small'; remove.textContent = '삭제'; remove.dataset.removeAttachment = '';
          row.append(img,title,hidden,remove); list.append(row);
        } catch (_) {errors.push(`${file.name}: 네트워크 오류가 발생했습니다. 다시 시도해주세요.`);}
      }
    } finally {
      uploading = false; save.disabled = false; picker.disabled = false; picker.value = ''; status.textContent = '';
      if (errors.length) showError(errors.join(' / '));
    }
  }
  attachmentForm.querySelector('[data-pick-upload]').addEventListener('click', () => {if (!uploading) picker.click();});
  picker.addEventListener('change', () => upload([...picker.files]));
  attachmentForm.querySelector('[data-upload-retry]').addEventListener('click', () => {if (!uploading) picker.click();});
  dropzone.addEventListener('dragover', e => {e.preventDefault(); dropzone.classList.add('dragging');});
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragging'));
  dropzone.addEventListener('drop', e => {e.preventDefault(); dropzone.classList.remove('dragging'); upload([...e.dataTransfer.files]);});
  attachmentForm.addEventListener('submit', e => {if (uploading) {e.preventDefault(); showError('업로드가 완료된 후 저장해주세요.');}});
}
