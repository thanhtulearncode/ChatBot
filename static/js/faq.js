function openModal() {
  const modal = document.getElementById("addModal");
  modal.style.display = "flex";
  // Focus sur le premier champ pour l'ergonomie
  setTimeout(() => modal.querySelector("input").focus(), 100);
}

function closeModal() {
  document.getElementById("addModal").style.display = "none";
}

// Fermer la modale si on clique sur le fond gris
document.getElementById("addModal").addEventListener("click", function (e) {
  if (e.target === this) closeModal();
});

// Fermer avec la touche Echap
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") closeModal();
});
