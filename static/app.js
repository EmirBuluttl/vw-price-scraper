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
    let priceMode = "campaign";
    let pollInterval = null;

    // Analytics Modal State
    let activeAnalyticsVariantId = null;
    let analyticsRawHistory = [];
    let priceChartInstance = null;

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

    const independentBrandsSubsection = document.getElementById("independent-brands-subsection");
    const independentPills = document.querySelectorAll("#independent-pills-container .pill-btn");

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
    const btnResetFilters = document.getElementById("btn-reset-filters");

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

    const inputAnalyticsStartDate = document.getElementById("input-analytics-start-date");
    const inputAnalyticsEndDate = document.getElementById("input-analytics-end-date");
    const quickDateBtns = document.querySelectorAll(".quick-date-btn");

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

    // Event Listeners: 3 Ana Grup Butonu Geçişi
    oemTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            oemTabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            currentGroup = tab.dataset.group;
            currentBrand = "all";
            currentModel = "all";

            // Marka seçilmediği için Model Bar gizlenir
            modelSubsectionBar.classList.add("hidden");

            if (currentGroup === "tofas") {
                document.getElementById("brand-pills").classList.add("hidden");
                independentBrandsSubsection.classList.add("hidden");
                tofasBrandsSubsection.classList.remove("hidden");
                tofasPills.forEach(p => {
                    if (p.dataset.brand === "all") p.classList.add("active");
                    else p.classList.remove("active");
                });
            } else if (currentGroup === "independent") {
                document.getElementById("brand-pills").classList.add("hidden");
                tofasBrandsSubsection.classList.add("hidden");
                independentBrandsSubsection.classList.remove("hidden");
                independentPills.forEach(p => {
                    if (p.dataset.brand === "all") p.classList.add("active");
                    else p.classList.remove("active");
                });
            } else {
                tofasBrandsSubsection.classList.add("hidden");
                independentBrandsSubsection.classList.add("hidden");
                document.getElementById("brand-pills").classList.remove("hidden");
                brandPills.forEach(p => {
                    if (p.dataset.brand === "all") p.classList.add("active");
                    else p.classList.remove("active");
                });
            }

            fetchPrices();
        });
    });

    // Event Listeners: Brand Pills (Tüm Markalar Sekmesi)
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

    // Event Listeners: Tofaş Brand Pills (Tofaş Grubu Sekmesi)
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

    // Event Listeners: Bağımsız Brand Pills (Bağımsız Markalar Sekmesi)
    independentPills.forEach(pill => {
        pill.addEventListener("click", () => {
            independentPills.forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            currentBrand = pill.dataset.brand;
            currentModel = "all";

            loadModelSubsection();
            fetchPrices();
        });
    });

    // Event Listener: Filtreleri Temizle Butonu
    if (btnResetFilters) {
        btnResetFilters.addEventListener("click", () => {
            currentGroup = "all";
            currentBrand = "all";
            currentModel = "all";
            searchQuery = "";
            fuelFilter = "all";
            bodyFilter = "all";
            transFilter = "all";
            statusFilter = "all";
            yearFilter = "all";
            minPrice = null;
            maxPrice = null;
            sortBy = "price_asc";

            // Reset UI inputs
            inputSearch.value = "";
            btnClearSearch.style.display = "none";
            inputMinPrice.value = "";
            inputMaxPrice.value = "";
            selectYear.value = "all";
            selectStatus.value = "all";
            selectFuel.value = "all";
            selectBody.value = "all";
            selectSort.value = "price_asc";

            // Reset Group Tabs
            oemTabs.forEach(t => {
                if (t.dataset.group === "all") t.classList.add("active");
                else t.classList.remove("active");
            });

            tofasBrandsSubsection.classList.add("hidden");
            independentBrandsSubsection.classList.add("hidden");
            document.getElementById("brand-pills").classList.remove("hidden");
            brandPills.forEach(p => {
                if (p.dataset.brand === "all") p.classList.add("active");
                else p.classList.remove("active");
            });

            modelSubsectionBar.classList.add("hidden");

            fetchPrices();
        });
    }

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

    const selectPriceMode = document.getElementById("select-price-mode");
    if (selectPriceMode) {
        selectPriceMode.addEventListener("change", (e) => {
            priceMode = e.target.value;
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

    // Analytics Modal Date Filter Controls
    if (inputAnalyticsStartDate) {
        inputAnalyticsStartDate.addEventListener("change", () => filterAnalyticsByDate());
    }
    if (inputAnalyticsEndDate) {
        inputAnalyticsEndDate.addEventListener("change", () => filterAnalyticsByDate());
    }

    quickDateBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            quickDateBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            const days = btn.dataset.days;
            if (days === "all") {
                inputAnalyticsStartDate.value = "";
                inputAnalyticsEndDate.value = "";
            } else {
                const d = new Date();
                d.setDate(d.getDate() - parseInt(days, 10));
                inputAnalyticsStartDate.value = d.toISOString().split("T")[0];
                inputAnalyticsEndDate.value = new Date().toISOString().split("T")[0];
            }
            filterAnalyticsByDate();
        });
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
                            <span class="brand-modal-title">${getBrandIconHtml(b.brand)} ${b.brand}</span>
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
        // KURAL: Kullanıcı spesifik bir marka butonuna basmadığı sürece (currentBrand === 'all') modeller KESİNLİKLE AÇILMAZ!
        if (currentBrand === "all") {
            modelSubsectionBar.classList.add("hidden");
            modelPillsContainer.innerHTML = "";
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

            // Brand Logo & Badge
            const brandIcon = getBrandIconHtml(item.brand);

            // Fiyat Gösterim Modu (Net Kampanyalı vs MSRP Liste Fiyatı vs İkili Karşılaştırma)
            const cp = item.campaign_price_int || item.price_int;
            const lp = item.list_price_int || item.price_int;
            const disc = item.discount_amount_int || 0;
            const discPct = item.discount_pct || 0;

            let priceDisplayHtml = "";
            if (priceMode === "list") {
                priceDisplayHtml = `<span class="price-val text-blue">${formatMoney(lp)}</span> <span class="price-mode-tag tag-msrp">MSRP</span>`;
            } else if (priceMode === "both") {
                if (disc > 0) {
                    priceDisplayHtml = `
                        <div class="price-both-container">
                            <span class="price-val text-green">${formatMoney(cp)}</span>
                            <s class="strikethrough-price" title="Tavsiye Edilen Liste Fiyatı">${formatMoney(lp)}</s>
                            <span class="badge-discount-tag" title="Kampanya İndirimi"><i class="fa-solid fa-fire"></i> -${formatMoney(disc)} (%${discPct})</span>
                        </div>
                    `;
                } else {
                    priceDisplayHtml = `<span class="price-val">${formatMoney(cp)}</span>`;
                }
            } else {
                // campaign mode (default)
                priceDisplayHtml = `<span class="price-val">${formatMoney(cp)}</span>`;
            }

            html += `
                <tr class="price-row" data-variant-id="${item.variant_id}">
                    <td><span class="brand-badge brand-${(item.brand || '').toLowerCase().replace(/\s+/g, '')}">${brandIcon} ${item.brand}</span></td>
                    <td class="font-bold text-main">${item.model_name}</td>
                    <td class="variant-name">${item.variant}</td>
                    <td>${attrHtml || '-'}</td>
                    <td>${priceDisplayHtml}</td>
                    <td>${diffHtml}</td>
                    <td><span class="date-badge"><i class="fa-regular fa-clock"></i> ${dateStr}</span></td>
                    <td>
                        <button class="btn-history-view" data-variant-id="${item.variant_id}" title="Fiyat Geçmişi & Trend Grafiğini Gör">
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
            activeAnalyticsVariantId = variantId;
            historyTimelineContainer.innerHTML = `<div class="text-center py-4"><i class="fa-solid fa-spinner fa-spin fa-2x"></i><p class="mt-2">Fiyat analizi ve geçmiş veriler yükleniyor...</p></div>`;
            historyModal.classList.remove("hidden");

            const res = await fetch(`/api/variant/${variantId}/history`);
            if (!res.ok) throw new Error("Geçmiş çekilemedi");
            const data = await res.json();

            const v = data.variant;
            analyticsRawHistory = data.history || [];

            historyModalTitle.innerHTML = `<i class="fa-solid fa-chart-line text-accent"></i> ${getBrandIconHtml(v.brand)} ${v.brand} ${v.model_name}`;
            historyModalSubtitle.textContent = `${v.variant} (${v.model_year || '2026'} Model • ${v.fuel_type || ''} • ${v.transmission || ''})`;

            renderAnalyticsModalData(analyticsRawHistory);
        } catch (err) {
            console.error("History modal error:", err);
            historyTimelineContainer.innerHTML = `<p class="text-danger text-center py-4">Geçmiş veriler yüklenirken hata oluştu.</p>`;
        }
    }

    function filterAnalyticsByDate() {
        if (!analyticsRawHistory || analyticsRawHistory.length === 0) return;

        const sVal = inputAnalyticsStartDate.value;
        const eVal = inputAnalyticsEndDate.value;

        let filtered = analyticsRawHistory.filter(h => {
            const hDate = h.scraped_date;
            if (sVal && hDate < sVal) return false;
            if (eVal && hDate > eVal) return false;
            return true;
        });

        renderAnalyticsModalData(filtered.length > 0 ? filtered : analyticsRawHistory);
    }

    function renderAnalyticsModalData(historyList) {
        if (!historyList || historyList.length === 0) {
            historyTimelineContainer.innerHTML = `<p class="text-muted text-center py-4">Seçilen tarihler arasında kayıt bulunamadı.</p>`;
            return;
        }

        // Compute KPIs
        const startPrice = historyList[0].price_int;
        const startDate = historyList[0].scraped_date;
        const latestPrice = historyList[historyList.length - 1].price_int;
        const latestDate = historyList[historyList.length - 1].scraped_date;
        const minPrice = Math.min(...historyList.map(h => h.price_int));
        const maxPrice = Math.max(...historyList.map(h => h.price_int));

        const netDiff = latestPrice - startPrice;
        const netPct = startPrice > 0 ? ((netDiff / startPrice) * 100).toFixed(2) : "0.00";

        kpiStartPrice.textContent = formatMoney(startPrice);
        kpiStartDate.textContent = `Tarih: ${startDate}`;
        kpiLatestPrice.textContent = formatMoney(latestPrice);
        kpiLatestDate.textContent = `Son Tarih: ${latestDate}`;
        kpiMinMaxPrice.textContent = `${formatMoney(minPrice)} / ${formatMoney(maxPrice)}`;

        if (netDiff > 0) {
            kpiNetDiff.textContent = `+${formatMoney(netDiff)}`;
            kpiNetDiff.className = "kpi-value text-green";
            kpiNetPct.textContent = `+%${netPct} Zam`;
            kpiNetPct.className = "kpi-sub text-green-sub";
        } else if (netDiff < 0) {
            kpiNetDiff.textContent = formatMoney(netDiff);
            kpiNetDiff.className = "kpi-value text-red";
            kpiNetPct.textContent = `%${netPct} İndirim`;
            kpiNetPct.className = "kpi-sub text-red-sub";
        } else {
            kpiNetDiff.textContent = "0 ₺";
            kpiNetDiff.className = "kpi-value text-white";
            kpiNetPct.textContent = "Değişim Yok (%0.0)";
            kpiNetPct.className = "kpi-sub text-muted";
        }

        // Render Table
        let timelineHtml = `
            <table class="analytics-table">
                <thead>
                    <tr>
                        <th>Taram Tarihi</th>
                        <th>Fiyat (TL)</th>
                        <th>Fark Tipi</th>
                        <th>Net Fark</th>
                        <th>Değişim (%)</th>
                    </tr>
                </thead>
                <tbody>
        `;

        historyList.forEach((h, idx) => {
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
                    <td><i class="fa-regular fa-calendar-check text-muted"></i> ${h.scraped_date}</td>
                    <td class="font-bold">${formatMoney(h.price_int)}</td>
                    <td>${badge}</td>
                    <td class="${h.price_diff > 0 ? 'text-green' : (h.price_diff < 0 ? 'text-red' : '')}">${diffText}</td>
                    <td class="${h.price_diff > 0 ? 'text-green' : (h.price_diff < 0 ? 'text-red' : '')}">${pctText}</td>
                </tr>
            `;
        });
        timelineHtml += `</tbody></table>`;

        historyTimelineContainer.innerHTML = timelineHtml;

        // Render Chart.js Trend Line Graph
        renderTrendChart(historyList);
    }

    function renderTrendChart(historyList) {
        const ctx = document.getElementById("priceTrendChart");
        if (!ctx) return;

        if (priceChartInstance) {
            priceChartInstance.destroy();
        }

        const labels = historyList.map(h => h.scraped_date);
        const prices = historyList.map(h => h.price_int);
        const pointColors = historyList.map(h => h.price_diff > 0 ? "#10b981" : (h.price_diff < 0 ? "#ef4444" : "#6366f1"));

        priceChartInstance = new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: [{
                    label: "Fiyat Değişimi (TL)",
                    data: prices,
                    borderColor: "#6366f1",
                    backgroundColor: "rgba(99, 102, 241, 0.15)",
                    borderWidth: 3,
                    fill: true,
                    tension: 0.35,
                    pointBackgroundColor: pointColors,
                    pointRadius: 6,
                    pointHoverRadius: 9
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return "Fiyat: " + formatMoney(context.raw);
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: "#9ca3af" },
                        grid: { color: "rgba(255, 255, 255, 0.05)" }
                    },
                    y: {
                        ticks: {
                            color: "#9ca3af",
                            callback: function(value) {
                                return (value / 1000000).toFixed(2) + "M ₺";
                            }
                        },
                        grid: { color: "rgba(255, 255, 255, 0.05)" }
                    }
                }
            }
        });
    }

    function getBrandIconHtml(brandName) {
        const b = (brandName || '').toLowerCase();
        if (b.includes('volkswagen') || b.includes('vw')) {
            return `<svg class="brand-svg-logo text-blue" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-3.8-12.8l2.3 6.9h3l2.3-6.9h-1.8l-1.3 4.4-1.3-4.4h-1.4l-1.3 4.4-1.3-4.4H8.2z"/></svg>`;
        }
        if (b.includes('ford')) {
            return `<svg class="brand-svg-logo text-blue" viewBox="0 0 24 24" fill="currentColor"><path d="M12 5C5.4 5 0 8.1 0 12s5.4 7 12 7 12-3.1 12-7-5.4-7-12-7zm4.5 9.2c-.8.6-2.1.8-3.6.8-2.5 0-4.2-.7-4.2-2.1 0-.9.8-1.5 2.1-1.7l1.5-.2c.8-.1 1.3-.3 1.3-.7 0-.4-.4-.6-1.1-.6-.9 0-2.1.3-3 .8l-.5-1.2c1.1-.6 2.6-1 3.8-1 1.9 0 3 1 3 2.3 0 .4-.1.9-.3 1.4l-.5 1.5z"/></svg>`;
        }
        if (b.includes('fiat')) {
            return `<svg class="brand-svg-logo text-red" viewBox="0 0 24 24" fill="currentColor"><path d="M4 4h16v16H4V4zm3 3v10h2V7H7zm4 0v10h2V7h-2zm4 0v10h2V7h-2z"/></svg>`;
        }
        if (b.includes('renault')) {
            return `<svg class="brand-svg-logo text-yellow" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L4 12l8 10 8-10L12 2zm0 3.8L16.2 12 12 18.2 7.8 12 12 5.8z"/></svg>`;
        }
        if (b.includes('peugeot')) {
            return `<svg class="brand-svg-logo text-blue" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-3zm1 14.5h-2v-4h-1v-2h3v6z"/></svg>`;
        }
        if (b.includes('opel')) {
            return `<svg class="brand-svg-logo text-yellow" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.5 8.5l-5 3.5h3.5l-4.5 3.5 1.5-4h-3.5l4-3h-2.5z"/></svg>`;
        }
        if (b.includes('citroën') || b.includes('citroen')) {
            return `<svg class="brand-svg-logo text-red" viewBox="0 0 24 24" fill="currentColor"><path d="M12 3L4 9l2 1.5L12 6l6 4.5L20 9l-8-6zm0 7l-8 6 2 1.5 6-4.5 6 4.5 2-1.5-8-6z"/></svg>`;
        }
        if (b.includes('jeep')) {
            return `<svg class="brand-svg-logo text-green" viewBox="0 0 24 24" fill="currentColor"><path d="M3 6v12h2V6H3zm4 0v12h2V6H7zm4 0v12h2V6h-2zm4 0v12h2V6h-2zm4 0v12h2V6h-2z"/></svg>`;
        }
        if (b.includes('alfa')) {
            return `<svg class="brand-svg-logo text-red" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 5h2v3h3v2h-3v5h-2v-5H8v-2h3V7z"/></svg>`;
        }
        if (b.includes('ds')) {
            return `<svg class="brand-svg-logo text-purple" viewBox="0 0 24 24" fill="currentColor"><path d="M6 4h4l6 8-6 8H6l6-8-6-8zm6 0h6l-3 4-3-4z"/></svg>`;
        }
        if (b.includes('maserati')) {
            return `<svg class="brand-svg-logo text-blue" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l-2 5 2 2 2-2-2-5zm-5 4v6l3-3-3-3zm10 0l-3 3 3 3V6zm-6 7v9h2v-9h-2z"/></svg>`;
        }
        if (b.includes('skoda')) {
            return `<svg class="brand-svg-logo text-green" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 14h-2l1-4h3l-2 4zm2-6h-6l1-3h6l-1 3z"/></svg>`;
        }
        if (b.includes('hyundai')) {
            return `<svg class="brand-svg-logo text-blue" viewBox="0 0 24 24" fill="currentColor"><path d="M12 3C6.5 3 2 7 2 12s4.5 9 10 9 10-4 10-9-4.5-9-10-9zm3.5 12.5l-2-7h-3l2 7h-2l-2-7H7l2.5 9h2l1.5-5h2l-1.5 5h2z"/></svg>`;
        }
        if (b.includes('toyota')) {
            return `<svg class="brand-svg-logo text-red" viewBox="0 0 24 24" fill="currentColor"><path d="M12 4c-5.5 0-10 2.2-10 5s4.5 5 10 5 10-2.2 10-5-4.5-5-10-5zm0 8.5c-3.3 0-6-1.1-6-2.5s2.7-2.5 6-2.5 6 1.1 6 2.5-2.7 2.5-6 2.5zm0-10.5C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm0 18c-4.4 0-8-3.6-8-8 0-1.8.6-3.4 1.7-4.7 1.8 1.4 4.2 2.2 6.3 2.2s4.5-.8 6.3-2.2c1.1 1.3 1.7 2.9 1.7 4.7 0 4.4-3.6 8-8 8z"/></svg>`;
        }
        if (b.includes('kia')) {
            return `<svg class="brand-svg-logo text-red" viewBox="0 0 24 24" fill="currentColor"><path d="M3 8v8h2v-3.5L7.5 16H10l-3.2-4.5L10 8H7.5L5.5 11V8H3zm8 0v8h2.5V8H11zm5 0l-3 8h2.2l.6-1.8h2.4l.6 1.8H21l-3-8h-2zm.8 2.2l.8 2.6h-1.6l.8-2.6z"/></svg>`;
        }
        if (b.includes('chery')) {
            return `<svg class="brand-svg-logo text-red" viewBox="0 0 24 24" fill="currentColor"><path d="M12 4L3 10l9 6 9-6-9-6zm0 4.2L16.5 10 12 11.8 7.5 10 12 8.2zM4 14l8 5 8-5v2.5l-8 5-8-5V14z"/></svg>`;
        }
        if (b.includes('dacia')) {
            return `<svg class="brand-svg-logo text-yellow" viewBox="0 0 24 24" fill="currentColor"><path d="M4 7h6v3H7v4h3v3H4V7zm10 0h6v10h-6v-3h3v-4h-3V7z"/></svg>`;
        }
        return `<svg class="brand-svg-logo" viewBox="0 0 24 24" fill="currentColor"><path d="M18.92 6.01C18.72 5.42 18.16 5 17.5 5h-11c-.66 0-1.21.42-1.42 1.01L3 12v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-8l-2.08-5.99zM6.85 7h10.29l1.04 3H5.81l1.04-3zM19 17H5v-4h14v4z"/></svg>`;
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
