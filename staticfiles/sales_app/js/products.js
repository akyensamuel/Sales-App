// Product search filter for products.html
document.addEventListener('DOMContentLoaded', function() {
	const searchInput = document.getElementById('productSearch');
	const tableBody = document.getElementById('productsTableBody');
	if (!searchInput || !tableBody) return;

	searchInput.addEventListener('input', function() {
		const filter = searchInput.value.toLowerCase();
		const rows = tableBody.querySelectorAll('.product-row');
		let anyVisible = false;
		rows.forEach(row => {
			const nameCell = row.querySelector('.product-name');
			if (nameCell) {
				const name = nameCell.textContent.toLowerCase();
				if (name.includes(filter)) {
					row.style.display = '';
					anyVisible = true;
				} else {
					row.style.display = 'none';
				}
			}
		});
		// Show/hide empty message row if present
		const emptyRow = tableBody.querySelector('tr td[colspan]');
		if (emptyRow) {
			emptyRow.parentElement.style.display = anyVisible ? 'none' : '';
		}
	});
});
