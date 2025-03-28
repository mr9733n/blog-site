<!-- ImageViewer.svelte -->
<script>
  import { onMount, onDestroy } from 'svelte';

  // Создаем переменные для отслеживания состояния модального окна
  let isModalOpen = false;
  let currentImageSrc = '';
  let modalElement;

  // Функция для открытия модального окна с изображением
  export function openImage(src) {
    currentImageSrc = src;
    isModalOpen = true;
  }

  // Обработчик нажатия клавиши ESC
  function handleKeyDown(e) {
    if (e.key === 'Escape' && isModalOpen) {
      isModalOpen = false;
    }
  }

  // Добавляем и удаляем обработчик при монтировании/размонтировании компонента
  onMount(() => {
    document.addEventListener('keydown', handleKeyDown);

    // Добавляем глобальную функцию для возможности вызова из обычного HTML
    window.openImageViewer = openImage;

    // Настраиваем делегирование событий для всех изображений с классом clickable-image
    document.body.addEventListener('click', (e) => {
      if (e.target && e.target.classList.contains('clickable-image')) {
        openImage(e.target.src);
        e.preventDefault();
      }
    });
  });

  onDestroy(() => {
    document.removeEventListener('keydown', handleKeyDown);

    // Удаляем глобальную функцию при размонтировании
    delete window.openImageViewer;

    // Удаляем обработчик событий
    document.body.removeEventListener('click', (e) => {
      if (e.target && e.target.classList.contains('clickable-image')) {
        openImage(e.target.src);
        e.preventDefault();
      }
    });
  });

  // Закрытие модального окна при клике вне изображения
  function handleModalClick(e) {
    if (e.target === modalElement) {
      isModalOpen = false;
    }
  }
</script>

<!-- Модальное окно для просмотра изображений -->
{#if isModalOpen}
  <div
    class="image-modal"
    bind:this={modalElement}
    on:click={handleModalClick}
  >
    <div class="modal-content">
      <span class="close-modal" on:click={() => isModalOpen = false}>&times;</span>
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
    top: -40px;
    right: 0;
    color: #f1f1f1;
    font-size: 40px;
    font-weight: bold;
    cursor: pointer;
    transition: color 0.2s;
  }

  .close-modal:hover {
    color: var(--accent-color, #007bff);
  }

  /* Стили для адаптивных экранов */
  @media (max-width: 768px) {
    .modal-content img {
      max-height: 80vh;
    }

    .close-modal {
      top: -35px;
      right: 0;
      font-size: 35px;
    }
  }
</style>