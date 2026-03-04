// Product search filter for products.html
document.addEventListener('DOMContentLoaded', function() {
	const searchInput = document.getElementById('productSearch');
	if (!searchInput) {
		console.log('Search input not found');
		return;
	}

	const tableBody = document.getElementById('productsTableBody');
	const cardBody = document.getElementById('productsCardBody');
	
	console.log('Search setup: tableBody=', !!tableBody, 'cardBody=', !!cardBody);

	// Only add event listener, don't interfere with initial display
	searchInput.addEventListener('input', function() {
		const filter = searchInput.value.toLowerCase().trim();
		console.log('Search filter:', filter);
		
		// Only apply filtering if there's actual search text
		if (filter === '') {
			// Show all products when search is empty
			if (tableBody) {
				tableBody.querySelectorAll('.product-row').forEach(row => {
					row.style.display = '';
				});
				const emptyRow = tableBody.querySelector('tr td[colspan]');
				if (emptyRow) {
					emptyRow.parentElement.style.display = 'none';
				}
			}
			if (cardBody) {
				cardBody.querySelectorAll('.product-row').forEach(card => {
					card.style.display = '';
				});
				const emptyDiv = cardBody.querySelector('.text-center');
				if (emptyDiv) {
					emptyDiv.style.display = 'none';
				}
			}
			console.log('Search cleared, showing all products');
			return;
		}
		
		console.log('Applying search filter');
		
		// Filter desktop table view
		if (tableBody) {
			const rows = tableBody.querySelectorAll('.product-row');
			console.log('Table rows found:', rows.length);
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
			console.log('Table filtered, visible:', anyVisible);
		}
		
		// Filter mobile card view
		if (cardBody) {
			const cards = cardBody.querySelectorAll('.product-row');
			console.log('Card rows found:', cards.length);
			let anyVisible = false;
			cards.forEach(card => {
				const nameCell = card.querySelector('.product-name');
				if (nameCell) {
					const name = nameCell.textContent.toLowerCase();
					if (name.includes(filter)) {
						card.style.display = '';
						anyVisible = true;
					} else {
						card.style.display = 'none';
					}
				}
			});
			// Show/hide empty message if present
			const emptyDiv = cardBody.querySelector('.text-center');
			if (emptyDiv) {
				emptyDiv.style.display = anyVisible ? 'none' : '';
			}
			console.log('Cards filtered, visible:', anyVisible);
		}
	});
});
