// Product search filter for products.html using AJAX
document.addEventListener('DOMContentLoaded', function() {
	const searchInput = document.getElementById('productSearch');
	if (!searchInput) {
		console.log('Search input not found');
		return;
	}

	console.log('Search setup initialized');
	let searchTimeout;

	// Listen to input changes
	searchInput.addEventListener('input', function() {
		clearTimeout(searchTimeout);
		const searchTerm = searchInput.value.trim();
		
		// Debounce the search (wait 300ms after user stops typing)
		searchTimeout = setTimeout(function() {
			performAjaxSearch(searchTerm);
		}, 300);
	});

	// Also allow Enter key for immediate search
	searchInput.addEventListener('keypress', function(e) {
		if (e.key === 'Enter') {
			e.preventDefault();
			clearTimeout(searchTimeout);
			const searchTerm = searchInput.value.trim();
			performAjaxSearch(searchTerm);
		}
	});

	function performAjaxSearch(searchTerm) {
		console.log('Performing AJAX search for:', searchTerm);

		if (searchTerm === '') {
			// Clear search - show all products
			console.log('Search cleared, showing all products');
			fetch('/sales/api/products/?q=')
				.then(response => response.json())
				.then(products => {
					updateProductsDisplay(products);
				})
				.catch(error => console.error('Error fetching products:', error));
		} else {
			// Fetch matching products from API
			fetch('/sales/api/products/?q=' + encodeURIComponent(searchTerm))
				.then(response => response.json())
				.then(data => {
					console.log('API returned ' + data.length + ' products');
					updateProductsDisplay(data);
				})
				.catch(error => console.error('Error fetching products:', error));
		}
	}

	function updateProductsDisplay(productsData) {
		// Convert API format to display format if needed
		let products = productsData;
		
		// If API returns wrapped format, extract the array
		if (productsData.results) {
			products = productsData.results;
		}

		console.log('Updating display with ' + products.length + ' products');

		// Update mobile view
		const mobileBody = document.getElementById('productsCardBody');
		if (mobileBody) {
			if (products.length === 0) {
				mobileBody.innerHTML = '<div class="text-center py-8 text-gray-500 dark:text-gray-400">No products found.</div>';
			} else {
				mobileBody.innerHTML = products.map(product => `
					<div class="product-row bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition">
						<div class="flex justify-between items-start mb-3">
							<div>
								<h3 class="font-semibold text-gray-900 dark:text-white text-sm product-name">${escapeHtml(product.text || product.name)}</h3>
								<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">SKU: #${product.id}</p>
							</div>
							<span class="text-green-700 dark:text-green-400 font-bold text-lg">₵${parseFloat(product.price || 0).toFixed(2)}</span>
						</div>
						
						<div class="flex items-center justify-between mb-4 pt-3 border-t border-gray-200 dark:border-gray-700">
							<div>
								<p class="text-xs text-gray-600 dark:text-gray-400 mb-1">Stock Level</p>
								<span class="product-stock text-sm font-semibold ${product.stock < 50 ? 'text-red-600 dark:text-red-400 animate-pulse' : 'text-green-700 dark:text-green-400'}">
									${product.stock || 0} units
								</span>
								${product.stock < 50 ? '<span class="ml-2 text-xs bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200 px-2 py-1 rounded">Low Stock!</span>' : ''}
							</div>
						</div>
						
						<div class="flex gap-2">
							<a href="/sales/edit-product/${product.id}/" class="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow transition text-center">Edit</a>
							<a href="/sales/delete-product/${product.id}/" class="flex-1 px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold shadow transition text-center">Delete</a>
						</div>
					</div>
				`).join('');
			}
		}

		// Update desktop table view
		const tableBody = document.getElementById('productsTableBody');
		if (tableBody) {
			if (products.length === 0) {
				tableBody.innerHTML = '<tr><td colspan="4" class="px-6 py-4 text-center text-gray-500 dark:text-gray-400 text-sm">No products found.</td></tr>';
			} else {
				tableBody.innerHTML = products.map(product => `
					<tr class="bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800 transition product-row">
						<td class="px-6 py-4 font-medium text-gray-900 dark:text-white product-name text-sm">${escapeHtml(product.text || product.name)}</td>
						<td class="px-6 py-4 text-green-700 dark:text-green-400 font-semibold text-sm">₵${parseFloat(product.price || 0).toFixed(2)}</td>
						<td class="px-6 py-4 text-sm">
							<span class="product-stock font-semibold ${product.stock < 50 ? 'text-red-600 dark:text-red-400 animate-pulse' : 'text-green-700 dark:text-green-400'}">
								${product.stock || 0}
							</span>
							${product.stock < 50 ? '<span class="ml-2 text-xs bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200 px-2 py-1 rounded">Low!</span>' : ''}
						</td>
						<td class="px-6 py-4 text-sm">
							<div class="flex gap-2">
								<a href="/sales/edit-product/${product.id}/" class="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold transition">Edit</a>
								<a href="/sales/delete-product/${product.id}/" class="px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold transition">Delete</a>
							</div>
						</td>
					</tr>
				`).join('');
			}
		}
	}

	// Helper function to escape HTML special characters
	function escapeHtml(text) {
		const div = document.createElement('div');
		div.textContent = text;
		return div.innerHTML;
	}
});
