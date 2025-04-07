<!-- ImageViewer.svelte -->
<script>
  import { onMount, onDestroy } from 'svelte';

  // Создаем переменные для отслеживания состояния модального окна
  let isModalOpen = false;
  let currentImageSrc = '';
  let modalElement;
  let clickHandler;
  let closeButton;

  // Функция для открытия модального окна с изображением
  export function openImage(src) {
    console.log('Opening image modal with source:', src);
    currentImageSrc = src;
    isModalOpen = true;

    // Focus on close button for keyboard navigation after modal opens
    setTimeout(() => {
      if (closeButton) {
        closeButton.focus();
      }
    }, 50);
  }

  // Обработчик нажатия клавиши ESC
  function handleKeyDown(e) {
    if (e.key === 'Escape' && isModalOpen) {
      closeModal();
    }
  }

  // Обработчик для кнопки закрытия
  function handleCloseKeyDown(e) {
    // Handle Enter or Space key
    if (e.key === 'Enter' || e.key === ' ') {
      closeModal();
      e.preventDefault();
    }
  }

  // Централизованная функция закрытия модального окна
  function closeModal() {
    isModalOpen = false;
  }

  onMount(() => {
    document.addEventListener('keydown', handleKeyDown);
    window.openImageViewer = openImage;

    clickHandler = (e) => {
      console.log('Click event detected on:', e.target);

      // Проверка, если клик был по изображению с классом clickable-image
      if (e.target && e.target.tagName === 'IMG' && e.target.classList.contains('clickable-image')) {
        console.log('Image clicked:', e.target.src);
        openImage(e.target.src);
        e.preventDefault();
        return;
      }

      // Проверка, если клик был по ссылке
      if (e.target && e.target.tagName === 'A') {
        // Проверяем, есть ли в href путь к изображению (по расширению)
        const href = e.target.getAttribute('href');
        if (href && (
          href.endsWith('.jpg') || href.endsWith('.jpeg') ||
          href.endsWith('.png') || href.endsWith('.gif') ||
          href.endsWith('.webp') || href.startsWith('blob:')
        )) {
          console.log('Image link clicked:', href);
          openImage(href);
          e.preventDefault();
          return;
        }
      }
    };

    document.body.addEventListener('click', clickHandler);
  });

  onDestroy(() => {
    document.removeEventListener('keydown', handleKeyDown);
    delete window.openImageViewer;
    document.body.removeEventListener('click', clickHandler);
  });

  // Закрытие модального окна при клике вне изображения
  function handleModalClick(e) {
    if (e.target === modalElement) {
      closeModal();
    }
  }
</script>

<!-- Модальное окно для просмотра изображений -->
{#if isModalOpen}
  <div
    class="image-modal"
    bind:this={modalElement}
    on:click={handleModalClick}
    on:keydown={handleKeyDown}
    role="dialog"
    aria-modal="true"
    aria-labelledby="image-viewer-title"
  >
    <div class="modal-content">
      <span
        class="close-modal"
        on:click={closeModal}
        on:keydown={handleCloseKeyDown}
        tabindex="0"
        role="button"
        aria-label="Закрыть просмотр изображения"
        bind:this={closeButton}
      >&times;</span>
      <h2 id="image-viewer-title" class="sr-only">Просмотр изображения</h2>
      <img src={currentImageSrc} alt="Увеличенное изображение">
    </div>
  </div>
{/if}

<style>
  .image-modal {
    display: flex;
    position: fixed;
    z-index: 9999;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.9);
    align-items: center;
    justify-content: center;
    animation: fadeIn 0.3s;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .modal-content {
    position: relative;
    max-width: 90%;
    max-height: 90%;
  }

  .modal-content img {
    max-width: 100%;
    max-height: 90vh;
    margin: auto;
    display: block;
    border-radius: 5px;
    box-shadow: 0 0 20px rgba(0, 0, 0, 0.3);
  }

  .close-modal {
    position: absolute;
    top: -20px;
    right: 2px;
    color: #f1f1f1;
    font-size: 40px;
    font-weight: bold;
    cursor: pointer;
    transition: color 0.2s;
  }

  .close-modal:hover,
  .close-modal:focus {
    color: var(--accent-color, #007bff);
    outline: none;
  }

  /* Screen reader only class */
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border-width: 0;
  }

  /* Стили для адаптивных экранов */
  @media (max-width: 768px) {
    .modal-content img {
      max-height: 80vh;
    }

    .close-modal {
      right: 0;
      font-size: 35px;
    }
  }
</style>