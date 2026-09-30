const sidebar = document.querySelector('.sidebar');
const mainContent = document.querySelector('.main-content');

function toggleSidebar() {
    sidebar.classList.toggle('collapsed');
    mainContent.classList.toggle('expanded');
}