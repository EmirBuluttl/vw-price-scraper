/* ==========================================================================
   Kurumsal Araç Fiyat Takip & Analiz Dashboard — Frontend JS App
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
    // State
    let currentGroup = "all";
    let currentBrand = "all";
    let currentModel = "all";
    let searchQuery = "";
    let fuelFilter = "all";
    let bodyFilter = "all";
    let transFilter = "all";
    let statusFilter = "all";
    let yearFilter = "all";
    let minPrice = null;
    let maxPrice = null;
    let sortBy = "price_asc";
    let pollInterval = null;

    // DOM Elements
    const statTotalModels = document.getElementById("stat-total-models");
    const statBrandsCard = document.getElementById("stat-brands-card");
    const statBrandsCnt = document.getElementById("stat-brands-cnt");
    const statNewModels = document.getElementById("stat-new-models");
    const statNewVariants = document.getElementById("stat-new-variants");
    const statPriceChanges = document.getElementById("stat-price-changes");

    const oemTabs = document.querySelectorAll("#oem-group-pills .oem-tab");
    const brandPills = document.querySelectorAll("#brand-pills .pill-btn");
    const tofasBrandsSubsection = document.getElementById("tofas-brands-subsection");
    const tofasPills = document.querySelectorAll("#tofas-pills-container .pill-btn");
    const modelSubsectionBar = document.getElementById("model-subsection-bar");
    const modelPillsContainer = document.getElementById("model-pills-container");

    const inputSearch = document.getElementById("input-search");
    const btnClearSearch = document.getElementById("btn-clear-search");
    const inputMinPrice = document.getElementById("input-min-price");
    const inputMaxPrice = document.getElementById("input-max-price");
    const selectYear = document.getElementById("select-year");
    const selectStatus = document.getElementById("select-status");
    const selectFuel = document.getElementById("select-fuel");
    const selectBody = document.getElementById("select-body");
    const selectSort = document.getElementById("select-sort");

    const tbodyPrices = document.getElementById("tbody-prices");
    const lblRecordsCount = document.getElementById("lbl-records-count");

    const btnTriggerScrape = document.getElementById("btn-trigger-scrape");
    const scrapeModal = document.getElementById("scrape-modal");
    const modalScrapeMsg = document.getElementById("modal-scrape-msg");
    const modalProgressBar = document.getElementById("modal-progress-bar");

    // Brands Modal Elements
    const brandsModal = document.getElementById("brands-list-modal");
    const brandsGridContainer = document.getElementById("brands-grid-container");
    const btnCloseBrandsModal = document.getElementById("btn-close-brands-modal");

    // Price History Analytics Modal Elements
    const historyModal = document.getElementById("price-history-modal");
    const historyModalTitle = document.getElementById("history-modal-title");
    const historyModalSubtitle = document.getElementById("history-modal-subtitle");
    const historyTimelineContainer = document.getElementById("history-timeline-container");
    const btnCloseHistoryModal = document.getElementById("btn-close-history-modal");

    const kpiStartPrice = document.getElementById("kpi-start-price");
    const kpiStartDate = document.getElementById("kpi-start-date");
    const kpiLatestPrice = document.getElementById("kpi-latest-price");
    const kpiLatestDate = document.getElementById("kpi-latest-date");
    const kpiMinMaxPrice = document.getElementById("kpi-minmax-price");
    const kpiNetDiff = document.getElementById("kpi-net-diff");
    const kpiNetPct = document.getElementById("kpi-net-pct");

    // Initial Data Fetch
    fetchSummary();
    fetchPrices();

    // Event Listeners: 2 Ana Grup Butonu Geçişi
    oemTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            oemTabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            currentGroup = tab.dataset.group;
            currentBrand = "all";
            currentModel = "all";

            if (currentGroup === "tofas") {
                document.getElementById("brand-pills").classList.add("hidden");
                tofasBrandsSubsection.classList.remove("hidden");
                tofasPills.forEach(p => {
                    if (p.dataset.brand === "all") p.classList.add("active");
                    else p.classList.remove("active");
                });
            } else {
                tofasBrandsSubsection.classList.add("hidden");
                document.getElementById("brand-pills").classList.remove("hidden");
                brandPills.forEach(p => {
                    if (p.dataset.brand === "all") p.classList.add("active");
                    else p.classList.remove("active");
                });
            }

            loadModelSubsection();
            fetchPrices();
        });
    });

    // Event Listeners: Bağımsız Brand Pills (Tüm Markalar Barı)
    brandPills.forEach(pill => {
        pill.addEventListener("click", () => {
            brandPills.forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            currentBrand = pill.dataset.brand;
            currentModel = "all";

            loadModelSubsection();
            fetchPrices();
        });
    });

    // Event Listeners: Tofaş Brand Pills (Tofaş Grubu Barı)
    tofasPills.forEach(pill => {
        pill.addEventListener("click", () => {
            tofasPills.forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            currentBrand = pill.dataset.brand;
            currentModel = "all";

            loadModelSubsection();
            fetchPrices();
        });
    });

    // Search Input Debounce
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

    // Min / Max Price Filter Inputs
    let priceRangeDebounce = null;
    const handlePriceRangeChange = () => {
        clearTimeout(priceRangeDebounce);
        priceRangeDebounce = setTimeout(() => {
            minPrice = inputMinPrice.value ? parseInt(inputMinPrice.value, 10) : null;
            maxPrice = inputMaxPrice.value ? parseInt(inputMaxPrice.value, 10) : null;
            fetchPrices();
        }, 350);
    };

    inputMinPrice.addEventListener("input", handlePriceRangeChange);
    inputMaxPrice.addEventListener("input", handlePriceRangeChange);

    // Select Filters
    if (selectYear) {
        selectYear.addEventListener("change", (e) => {
            yearFilter = e.target.value;
            fetchPrices();
        });
    }

    selectStatus.addEventListener("change", (e) => {
        statusFilter = e.target.value;
        fetchPrices();
    });

    if (selectFuel) {
        selectFuel.addEventListener("change", (e) => {
            fuelFilter = e.target.value;
            fetchPrices();
        });
    }

    if (selectBody) {
        selectBody.addEventListener("change", (e) => {
            bodyFilter = e.target.value;
            fetchPrices();
        });
    }

    selectSort.addEventListener("change", (e) => {
        sortBy = e.target.value;
        fetchPrices();
    });

    btnTriggerScrape.addEventListener("click", () => {
        startScrape();
    });

    // Aktif Marka Kartı Tıklama -> Open Brands Modal
    if (statBrandsCard) {
        statBrandsCard.addEventListener("click", () => {
            openBrandsModal();
        });
    }

    if (btnCloseBrandsModal) {
        btnCloseBrandsModal.addEventListener("click", () => {
            brandsModal.classList.add("hidden");
        });
    }

    brandsModal.addEventListener("click", (e) => {
        if (e.target === brandsModal) brandsModal.classList.add("hidden");
    });

    if (btnCloseHistoryModal) {
        btnCloseHistoryModal.addEventListener("click", () => {
            historyModal.classList.add("hidden");
        });
    }

    historyModal.addEventListener("click", (e) => {
        if (e.target === historyModal) historyModal.classList.add("hidden");
    });

    // ─── API Fetch Functions ───────────────────────────────────────────────

    async function fetchSummary() {
        try {
            const res = await fetch("/api/summary");
            if (!res.ok) return;
            const data = await res.json();

            if (statTotalModels) statTotalModels.textContent = data.total_models || "0";
            if (statBrandsCnt) statBrandsCnt.textContent = data.brands ? data.brands.length : "17";
            if (statNewModels) statNewModels.textContent = data.new_models_cnt || "0";
            if (statNewVariants) statNewVariants.textContent = data.new_variants_cnt || "0";
            if (statPriceChanges) statPriceChanges.textContent = data.price_changes_cnt || "0";

            if (data.scrape_status && data.scrape_status.running) {
                showScrapeModal(data.scrape_status.message, data.scrape_status.progress);
                startPollingScrapeStatus();
            }
        } catch (err) {
            console.error("Summary fetch error:", err);
        }
    }

    async function openBrandsModal() {
        try {
            brandsGridContainer.innerHTML = `<div class="text-center py-4"><i class="fa-solid fa-spinner fa-spin fa-2x"></i><p class="mt-2">Markalar yükleniyor...</p></div>`;
            brandsModal.classList.remove("hidden");

            const res = await fetch("/api/brands");
            if (!res.ok) throw new Error("Markalar çekilemedi");
            const data = await res.json();

            const brands = data.brands || [];
            let html = "";

            brands.forEach(b => {
                const tofasBadge = b.is_tofas_group ? `<span class="badge badge-tofas"><i class="fa-solid fa-building"></i> Tofaş Grubu</span>` : `<span class="badge badge-other">Bağımsız Marka</span>`;
                html += `
                    <div class="brand-modal-card">
                        <div class="brand-modal-header">
                            <span class="brand-modal-title">${b.brand}</span>
                            ${tofasBadge}
                        </div>
                        <div class="brand-modal-stats">
                            <span><i class="fa-solid fa-car"></i> <strong>${b.active_vehicle_cnt}</strong> Aktif Araç</span>
                            <span><i class="fa-solid fa-layer-group"></i> <strong>${b.model_cnt}</strong> Model</span>
                        </div>
                    </div>
                `;
            });

            brandsGridContainer.innerHTML = html;
        } catch (err) {
            console.error("Brands modal error:", err);
            brandsGridContainer.innerHTML = `<p class="text-danger text-center py-4">Marka listesi yüklenirken hata oluştu.</p>`;
        }
    }

    async function loadModelSubsection() {
        // KURAL: Marka seçilmedikçe (currentBrand === 'all') modeller BUTON OLARAK LISTELENMEZ!
        if (currentBrand === "all") {
            modelSubsectionBar.classList.add("hidden");
            return;
        }

        try {
            const url = new URL("/api/models", window.location.origin);
            url.searchParams.append("brand", currentBrand);

            const res = await fetch(url);
            if (!res.ok) return;
            const data = await res.json();

            if (data.models && data.models.length > 0) {
                modelSubsectionBar.classList.remove("hidden");
                modelPillsContainer.innerHTML = "";

                // "Tüm Modeller" pill
                const allPill = document.createElement("button");
                allPill.className = `sub-pill-btn ${currentModel === "all" ? "active" : ""}`;
                allPill.textContent = "Tüm Modeller";
                allPill.addEventListener("click", () => {
                    document.querySelectorAll(".sub-pill-btn").forEach(p => p.classList.remove("active"));
                    allPill.classList.add("active");
                    currentModel = "all";
                    fetchPrices();
                });
                modelPillsContainer.appendChild(allPill);

                // Add model pills
                data.models.forEach(m => {
                    const pill = document.createElement("button");
                    pill.className = `sub-pill-btn ${currentModel === m.model_name ? "active" : ""}`;
                    pill.textContent = m.model_name;
                    pill.addEventListener("click", () => {
                        document.querySelectorAll(".sub-pill-btn").forEach(p => p.classList.remove("active"));
                        pill.classList.add("active");
                        currentModel = m.model_name;
                        fetchPrices();
                    });
                    modelPillsContainer.appendChild(pill);
                });
            } else {
                modelSubsectionBar.classList.add("hidden");
            }
        } catch (err) {
            console.error("Model subsection fetch error:", err);
        }
    }

    async function fetchPrices() {
        try {
            const url = new URL("/api/prices", window.location.origin);
            if (currentGroup !== "all") url.searchParams.append("group", currentGroup);
            if (currentBrand !== "all") url.searchParams.append("brand", currentBrand);
            if (currentModel !== "all") url.searchParams.append("model", currentModel);
            if (searchQuery) url.searchParams.append("search", searchQuery);
            if (yearFilter !== "all") url.searchParams.append("year", yearFilter);
            if (fuelFilter !== "all") url.searchParams.append("fuel", fuelFilter);
            if (bodyFilter !== "all") url.searchParams.append("body", bodyFilter);
            if (transFilter !== "all") url.searchParams.append("trans", transFilter);
            if (statusFilter !== "all") url.searchParams.append("status", statusFilter);
            if (minPrice) url.searchParams.append("min_price", minPrice);
            if (maxPrice) url.searchParams.append("max_price", maxPrice);

            url.searchParams.append("sort", sortBy);

            lblRecordsCount.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Yükleniyor...`;

            const res = await fetch(url);
            if (!res.ok) throw new Error("Fiyatlar çekilemedi");
            const data = await res.json();

            renderPricesTable(data.prices || []);
            lblRecordsCount.textContent = `${data.total || 0} Araç Listeleniyor (${data.target_date || 'En Güncel'})`;
        } catch (err) {
            console.error("Prices fetch error:", err);
            tbodyPrices.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center text-danger py-4">
                        <i class="fa-solid fa-triangle-exclamation fa-2x"></i>
                        <p class="mt-2">Veriler yüklenirken hata oluştu.</p>
                    </td>
                </tr>
            `;
            lblRecordsCount.textContent = "Hata";
        }
    }

    function renderPricesTable(prices) {
        if (!prices || prices.length === 0) {
            tbodyPrices.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-4 text-muted">
                        <i class="fa-solid fa-magnifying-glass fa-2x"></i>
                        <p class="mt-2">Kriterlere uygun araç bulunamadı.</p>
                    </td>
                </tr>
            `;
            return;
        }

        let html = "";
        prices.forEach(item => {
            // Fiyat Değişim Renkleri: Artanlar YEŞİL (.diff-up), Azalanlar KIRMIZI (.diff-down), Değişmeyenler BEYAZ (.diff-neutral)
            let diffHtml = "-";
            if (item.price_diff > 0) {
                diffHtml = `<span class="price-diff diff-up" title="Önceki Fiyat: ${formatMoney(item.previous_price_int)}"><i class="fa-solid fa-arrow-up"></i> +${formatMoney(item.price_diff)} (+%${item.price_change_pct})</span>`;
            } else if (item.price_diff < 0) {
                diffHtml = `<span class="price-diff diff-down" title="Önceki Fiyat: ${formatMoney(item.previous_price_int)}"><i class="fa-solid fa-arrow-down"></i> ${formatMoney(item.price_diff)} (%${item.price_change_pct})</span>`;
            } else {
                diffHtml = `<span class="price-diff diff-neutral">Sabit</span>`;
            }

            // Attributes & Model Year
            let attrHtml = "";
            if (item.model_year) attrHtml += `<span class="attr-pill attr-year">${item.model_year} Model</span> `;
            if (item.fuel_type) attrHtml += `<span class="attr-pill attr-fuel">${item.fuel_type}</span> `;
            if (item.body_type) attrHtml += `<span class="attr-pill attr-body">${item.body_type}</span> `;
            if (item.transmission) attrHtml += `<span class="attr-pill attr-trans">${item.transmission}</span> `;
            if (item.engine_power) attrHtml += `<span class="attr-pill attr-hp">${item.engine_power}</span>`;

            // Scraped Date Timestamp
            let dateStr = item.scraped_at ? item.scraped_at.replace("T", " ") : (item.scraped_date || "-");

            html += `
                <tr class="price-row" data-variant-id="${item.variant_id}">
                    <td><span class="brand-badge brand-${(item.brand || '').toLowerCase().replace(/\s+/g, '')}">${item.brand}</span></td>
                    <td class="font-bold text-main">${item.model_name}</td>
                    <td class="variant-name">${item.variant}</td>
                    <td>${attrHtml || '-'}</td>
                    <td class="price-val">${formatMoney(item.price_int)}</td>
                    <td>${diffHtml}</td>
                    <td><span class="date-badge"><i class="fa-regular fa-clock"></i> ${dateStr}</span></td>
                    <td>
                        <button class="btn-history-view" data-variant-id="${item.variant_id}" title="Fiyat Geçmişi & Analizini Gör">
                            <i class="fa-solid fa-chart-line"></i> Analiz
                        </button>
                    </td>
                </tr>
            `;
        });

        tbodyPrices.innerHTML = html;

        // Attach event listeners for history modal buttons
        document.querySelectorAll(".btn-history-view").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const variantId = btn.dataset.variantId;
                openPriceHistoryModal(variantId);
            });
        });
    }

    async function openPriceHistoryModal(variantId) {
        try {
            historyTimelineContainer.innerHTML = `<div class="text-center py-4"><i class="fa-solid fa-spinner fa-spin fa-2x"></i><p class="mt-2">Fiyat analizi ve geçmiş veriler yükleniyor...</p></div>`;
            historyModal.classList.remove("hidden");

            const res = await fetch(`/api/variant/${variantId}/history`);
            if (!res.ok) throw new Error("Geçmiş çekilemedi");
            const data = await res.json();

            const v = data.variant;
            const a = data.analytics || {};
            const history = data.history || [];

            historyModalTitle.innerHTML = `<i class="fa-solid fa-chart-line text-accent"></i> ${v.brand} ${v.model_name}`;
            historyModalSubtitle.textContent = `${v.variant} (${v.model_year || '2026'} Model • ${v.fuel_type || ''} • ${v.transmission || ''})`;

            // Populate KPI Cards
            kpiStartPrice.textContent = formatMoney(a.start_price);
            kpiStartDate.textContent = `Tarih: ${a.start_date}`;
            kpiLatestPrice.textContent = formatMoney(a.latest_price);
            kpiLatestDate.textContent = `Son Güncelleme: ${a.latest_date}`;
            kpiMinMaxPrice.textContent = `${formatMoney(a.min_price)} / ${formatMoney(a.max_price)}`;

            if (a.net_diff > 0) {
                kpiNetDiff.textContent = `+${formatMoney(a.net_diff)}`;
                kpiNetDiff.className = "kpi-value text-green";
                kpiNetPct.textContent = `+%${a.net_change_pct} Zam`;
                kpiNetPct.className = "kpi-sub text-green-sub";
            } else if (a.net_diff < 0) {
                kpiNetDiff.textContent = formatMoney(a.net_diff);
                kpiNetDiff.className = "kpi-value text-red";
                kpiNetPct.textContent = `%${a.net_change_pct} İndirim`;
                kpiNetPct.className = "kpi-sub text-red-sub";
            } else {
                kpiNetDiff.textContent = "0 ₺";
                kpiNetDiff.className = "kpi-value text-white";
                kpiNetPct.textContent = "Değişim Yok (%0.0)";
                kpiNetPct.className = "kpi-sub text-muted";
            }

            if (history.length === 0) {
                historyTimelineContainer.innerHTML = `<p class="text-muted text-center py-4">Bu araç için geçmiş kayıt bulunamadı.</p>`;
                return;
            }

            // Render Detailed Comparison Table
            let timelineHtml = `
                <table class="analytics-table">
                    <thead>
                        <tr>
                            <th>Taram Tarihi & Saati</th>
                            <th>Fiyat (TL)</th>
                            <th>Fark Tipi</th>
                            <th>Net Değişim (TL)</th>
                            <th>Değişim Oranı (%)</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            history.forEach((h, idx) => {
                let badge = `<span class="badge badge-neutral">Sabit</span>`;
                let diffText = "0 ₺";
                let pctText = "%0.00";

                if (h.price_diff > 0) {
                    badge = `<span class="badge badge-up"><i class="fa-solid fa-arrow-up"></i> Zam Gelen</span>`;
                    diffText = `+${formatMoney(h.price_diff)}`;
                    pctText = `+%${h.price_change_pct}`;
                } else if (h.price_diff < 0) {
                    badge = `<span class="badge badge-down"><i class="fa-solid fa-arrow-down"></i> Fiyatı Düşen</span>`;
                    diffText = formatMoney(h.price_diff);
                    pctText = `%${h.price_change_pct}`;
                } else if (idx === 0) {
                    badge = `<span class="badge badge-blue"><i class="fa-solid fa-flag-checkered"></i> Başlangıç</span>`;
                }

                timelineHtml += `
                    <tr>
                        <td><i class="fa-regular fa-calendar-check text-muted"></i> ${h.scraped_date} (${h.scraped_at ? h.scraped_at.split('T')[1] : ''})</td>
                        <td class="font-bold">${formatMoney(h.price_int)}</td>
                        <td>${badge}</td>
                        <td class="${h.price_diff > 0 ? 'text-green' : (h.price_diff < 0 ? 'text-red' : '')}">${diffText}</td>
                        <td class="${h.price_diff > 0 ? 'text-green' : (h.price_diff < 0 ? 'text-red' : '')}">${pctText}</td>
                    </tr>
                `;
            });
            timelineHtml += `</tbody></table>`;

            historyTimelineContainer.innerHTML = timelineHtml;
        } catch (err) {
            console.error("History modal error:", err);
            historyTimelineContainer.innerHTML = `<p class="text-danger text-center py-4">Geçmiş veriler yüklenirken hata oluştu.</p>`;
        }
    }

    // ─── Live Scraper & Polling ───────────────────────────────────────────

    async function startScrape() {
        try {
            const res = await fetch("/api/trigger-scrape", { method: "POST" });
            const data = await res.json();

            if (data.status === "started" || data.status === "running") {
                showScrapeModal(data.message, 0);
                startPollingScrapeStatus();
            } else if (data.status === "error") {
                alert(data.message);
            }
        } catch (err) {
            alert("Tarama başlatılırken hata oluştu!");
        }
    }

    function startPollingScrapeStatus() {
        if (pollInterval) clearInterval(pollInterval);

        pollInterval = setInterval(async () => {
            try {
                const res = await fetch("/api/summary");
                if (!res.ok) return;
                const data = await res.json();

                const status = data.scrape_status;
                if (status) {
                    showScrapeModal(status.message, status.progress);
                    if (!status.running) {
                        clearInterval(pollInterval);
                        setTimeout(() => {
                            hideScrapeModal();
                            fetchSummary();
                            fetchPrices();
                        }, 1000);
                    }
                }
            } catch (err) {
                console.error("Polling error:", err);
            }
        }, 1500);
    }

    function showScrapeModal(msg, progress) {
        modalScrapeMsg.textContent = msg || "Taranıyor...";
        modalProgressBar.style.width = `${progress || 0}%`;
        scrapeModal.classList.remove("hidden");
    }

    function hideScrapeModal() {
        scrapeModal.classList.add("hidden");
    }

    function formatMoney(amount) {
        if (amount === null || amount === undefined) return "-";
        return new Intl.NumberFormat("tr-TR", {
            style: "currency",
            currency: "TRY",
            maximumFractionDigits: 0
        }).format(amount);
    }
});
