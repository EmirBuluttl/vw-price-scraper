/* ==========================================================================
   Araç Fiyat Takip & Otomasyon Dashboard — Frontend JS App
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
    // State
    let currentBrand = "all";
    let searchQuery = "";
    let onlyNew = false;
    let onlyChanges = false;
    let sortBy = "price_asc";
    let pollInterval = null;

    // DOM Elements
    const statTotalModels = document.getElementById("stat-total-models");
    const statNewModels = document.getElementById("stat-new-models");
    const statNewVariants = document.getElementById("stat-new-variants");
    const statPriceChanges = document.getElementById("stat-price-changes");

    const brandPills = document.querySelectorAll("#brand-pills .pill-btn");
    const inputSearch = document.getElementById("input-search");
    const btnClearSearch = document.getElementById("btn-clear-search");
    const chkOnlyNew = document.getElementById("chk-only-new");
    const chkOnlyChanges = document.getElementById("chk-only-changes");
    const selectSort = document.getElementById("select-sort");
    
    const tbodyPrices = document.getElementById("tbody-prices");
    const lblRecordsCount = document.getElementById("lbl-records-count");
    
    const btnTriggerScrape = document.getElementById("btn-trigger-scrape");
    const scrapeModal = document.getElementById("scrape-modal");
    const modalScrapeMsg = document.getElementById("modal-scrape-msg");
    const modalProgressBar = document.getElementById("modal-progress-bar");

    // Initial Data Fetch
    fetchSummary();
    fetchPrices();

    // Event Listeners
    brandPills.forEach(pill => {
        pill.addEventListener("click", () => {
            brandPills.forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            currentBrand = pill.dataset.brand;
            fetchPrices();
        });
    });

    let searchDebounceTimeout = null;
    inputSearch.addEventListener("input", (e) => {
        searchQuery = e.target.value.trim();
        btnClearSearch.style.display = searchQuery ? "block" : "none";
        
        clearTimeout(searchDebounceTimeout);
        searchDebounceTimeout = setTimeout(() => {
            fetchPrices();
        }, 250);
    });

    btnClearSearch.addEventListener("click", () => {
        inputSearch.value = "";
        searchQuery = "";
        btnClearSearch.style.display = "none";
        fetchPrices();
    });

    chkOnlyNew.addEventListener("change", (e) => {
        onlyNew = e.target.checked;
        fetchPrices();
    });

    chkOnlyChanges.addEventListener("change", (e) => {
        onlyChanges = e.target.checked;
        fetchPrices();
    });

    selectSort.addEventListener("change", (e) => {
        sortBy = e.target.value;
        fetchPrices();
    });

    btnTriggerScrape.addEventListener("click", () => {
        startScrape();
    });

    // ─── API Fetch Functions ───────────────────────────────────────────────

    async function fetchSummary() {
        try {
            const res = await fetch("/api/summary");
            if (!res.ok) return;
            const data = await res.json();
            
            if (statTotalModels) statTotalModels.textContent = data.total_models || "0";
            if (statNewModels) statNewModels.textContent = data.new_models_cnt || "0";
            if (statNewVariants) statNewVariants.textContent = data.new_variants_cnt || "0";
            if (statPriceChanges) statPriceChanges.textContent = data.price_changes_cnt || "0";

            if (data.scrape_status && data.scrape_status.running) {
                showScrapeModal(data.scrape_status.message, data.scrape_status.progress);
                startStatusPolling();
            }
        } catch (err) {
            console.error("fetchSummary error:", err);
        }
    }

    async function fetchPrices() {
        tbodyPrices.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-4">
                    <i class="fa-solid fa-spinner fa-spin fa-2x"></i>
                    <p class="mt-2">Veriler yükleniyor...</p>
                </td>
            </tr>
        `;

        try {
            const params = new URLSearchParams({
                brand: currentBrand,
                search: searchQuery,
                only_new: onlyNew,
                only_changes: onlyChanges,
                sort: sortBy
            });

            const res = await fetch(`/api/prices?${params}`);
            if (!res.ok) throw new Error("API hatası");
            const data = await res.json();

            lblRecordsCount.textContent = `${data.total} kayıt bulundu (${data.target_date || ''})`;
            renderTable(data.prices);
        } catch (err) {
            console.error("fetchPrices error:", err);
            tbodyPrices.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-4 text-danger">
                        <i class="fa-solid fa-triangle-exclamation fa-2x"></i>
                        <p class="mt-2">Veriler yüklenirken hata oluştu.</p>
                    </td>
                </tr>
            `;
        }
    }

    function renderTable(prices) {
        if (!prices || prices.length === 0) {
            tbodyPrices.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-4 text-muted">
                        <i class="fa-solid fa-magnifying-glass fa-2x mb-2"></i>
                        <p>Kriterlere uygun araç kaydı bulunamadı.</p>
                    </td>
                </tr>
            `;
            return;
        }

        let html = "";
        prices.forEach(r => {
            const brand = r.brand || "—";
            const modelName = r.model_name || "—";
            const variant = r.variant || "—";
            const priceRaw = r.price_raw || "—";
            const source = r.source || "—";

            // Rozetler
            let badgesHtml = "";
            if (r.is_new_model === 1) {
                badgesHtml += `<span class="badge-new-model"><i class="fa-solid fa-wand-magic-sparkles"></i> YENİ MODEL</span> `;
            }
            if (r.is_new_variant === 1) {
                badgesHtml += `<span class="badge-new-variant"><i class="fa-solid fa-star"></i> YENİ PAKET</span> `;
            }
            if (r.price_diff && r.price_diff !== 0) {
                const diffFmt = new Intl.NumberFormat('tr-TR').format(Math.abs(r.price_diff));
                if (r.price_diff > 0) {
                    badgesHtml += `<span class="badge-price-up" title="Önceki Fiyat: ${new Intl.NumberFormat('tr-TR').format(r.previous_price_int)} TL"><i class="fa-solid fa-arrow-trend-up"></i> +${diffFmt} TL (%${r.price_change_pct})</span> `;
                } else {
                    badgesHtml += `<span class="badge-price-down" title="Önceki Fiyat: ${new Intl.NumberFormat('tr-TR').format(r.previous_price_int)} TL"><i class="fa-solid fa-arrow-trend-down"></i> -${diffFmt} TL (%${r.price_change_pct})</span> `;
                }
            }
            if (r.is_stale === 1) {
                badgesHtml += `<span class="badge-stale" title="Eski veriden kurtarıldı"><i class="fa-solid fa-clock-rotate-left"></i> STALE</span> `;
            }

            html += `
                <tr>
                    <td><span class="brand-badge">${brand}</span></td>
                    <td class="model-name">${modelName}</td>
                    <td class="variant-name">${variant}</td>
                    <td class="price-text">${priceRaw}</td>
                    <td>${badgesHtml || '<span class="text-subtle">-</span>'}</td>
                    <td><span class="source-tag">${source}</span></td>
                </tr>
            `;
        });

        tbodyPrices.innerHTML = html;
    }

    // ─── Scrape Trigger & Polling ─────────────────────────────────────────

    async function startScrape() {
        try {
            const res = await fetch("/api/trigger-scrape", { method: "POST" });
            const data = await res.json();
            showScrapeModal(data.message, 5);
            startStatusPolling();
        } catch (err) {
            alert("Tarama başlatılırken hata oluştu: " + err);
        }
    }

    function showScrapeModal(msg, progress) {
        scrapeModal.classList.remove("hidden");
        modalScrapeMsg.textContent = msg || "Tüm markalar taranıyor...";
        modalProgressBar.style.width = `${progress || 0}%`;
    }

    function hideScrapeModal() {
        scrapeModal.classList.add("hidden");
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    }

    function startStatusPolling() {
        if (pollInterval) clearInterval(pollInterval);

        pollInterval = setInterval(async () => {
            try {
                const res = await fetch("/api/summary");
                if (!res.ok) return;
                const data = await res.json();
                const status = data.scrape_status;

                if (status && status.running) {
                    showScrapeModal(status.message, status.progress);
                } else {
                    hideScrapeModal();
                    fetchSummary();
                    fetchPrices();
                }
            } catch (err) {
                console.error("polling error:", err);
            }
        }, 1500);
    }
});
