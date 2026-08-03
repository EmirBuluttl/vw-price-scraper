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
    let dateFilter = "all";
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
    const selectDateFilter = document.getElementById("select-date-filter");
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

    if (selectDateFilter) {
        selectDateFilter.addEventListener("change", (e) => {
            dateFilter = e.target.value;
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
            if (dateFilter !== "all") url.searchParams.append("date_filter", dateFilter);
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

            // Fiyat Güncelleme Tarihi Formatlama
            let dateFormatted = "-";
            if (item.scraped_at) {
                const parts = item.scraped_at.split("T");
                const dateParts = parts[0].split("-");
                const timeParts = parts[1] ? parts[1].substring(0, 5) : "";
                if (dateParts.length === 3) {
                    dateFormatted = `${dateParts[2]}.${dateParts[1]}.${dateParts[0]}`;
                    if (timeParts) dateFormatted += ` <small class="date-time-sub">${timeParts}</small>`;
                } else {
                    dateFormatted = item.scraped_at.replace("T", " ");
                }
            } else if (item.scraped_date) {
                const dateParts = item.scraped_date.split("-");
                if (dateParts.length === 3) dateFormatted = `${dateParts[2]}.${dateParts[1]}.${dateParts[0]}`;
                else dateFormatted = item.scraped_date;
            }

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
                    <td><span class="date-badge-updated" title="Fiyat Güncelleme Tarihi & Saati"><i class="fa-regular fa-calendar-check"></i> ${dateFormatted}</span></td>
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
        let filename = 'volkswagen.png';

        if (b.includes('volkswagen') || b.includes('vw')) filename = 'volkswagen.png';
        else if (b.includes('skoda')) filename = 'skoda.png';
        else if (b.includes('renault')) filename = 'renault.png';
        else if (b.includes('ford')) filename = 'ford.png';
        else if (b.includes('hyundai')) filename = 'hyundai.png';
        else if (b.includes('toyota')) filename = 'toyota.png';
        else if (b.includes('chery')) filename = 'chery.png';
        else if (b.includes('dacia')) filename = 'dacia.png';
        else if (b.includes('kia')) filename = 'kia.png';
        else if (b.includes('fiat')) filename = 'fiat.png';
        else if (b.includes('peugeot')) filename = 'peugeot.png';
        else if (b.includes('opel')) filename = 'opel.png';
        else if (b.includes('citroën') || b.includes('citroen')) filename = 'citroen.png';
        else if (b.includes('jeep')) filename = 'jeep.png';
        else if (b.includes('alfa')) filename = 'alfaromeo.png';
        else if (b.includes('ds')) filename = 'ds.png';
        else if (b.includes('maserati')) filename = 'maserati.png';

        return `<img src="/static/logos/${filename}" class="brand-logo-img" alt="${brandName}" />`;
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

    // ─── Feature 3: Smooth Number Counter Micro-Animation ──────────────────────
    function animateValue(element, start, end, duration = 600, isCurrency = false, prefix = '', suffix = '') {
        if (!element) return;
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            const currentVal = Math.floor(progress * (end - start) + start);
            element.textContent = prefix + (isCurrency ? formatMoney(currentVal) : currentVal.toLocaleString('tr-TR')) + suffix;
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    }

    // ─── Feature 5: Theme Toggle (Light / Dark Mode) ─────────────────────────
    const btnThemeToggle = document.getElementById("btn-theme-toggle");
    const themeIcon = document.getElementById("theme-icon");
    let currentTheme = localStorage.getItem("theme") || "dark";

    function applyTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("theme", theme);
        if (themeIcon) {
            if (theme === "light") {
                themeIcon.className = "fa-solid fa-moon";
                if (btnThemeToggle) btnThemeToggle.title = "Karanlık Temaya Geç";
            } else {
                themeIcon.className = "fa-solid fa-sun";
                if (btnThemeToggle) btnThemeToggle.title = "Aydınlık Temaya Geç";
            }
        }
    }

    if (btnThemeToggle) {
        applyTheme(currentTheme);
        btnThemeToggle.addEventListener("click", () => {
            currentTheme = currentTheme === "dark" ? "light" : "dark";
            applyTheme(currentTheme);
        });
    }

    // ─── Feature 2: Quick Data Summary Strip ──────────────────────────────────
    function updateQuickSummary(prices) {
        const qsAvgPrice = document.getElementById("qs-avg-price");
        const qsMinPrice = document.getElementById("qs-min-price");
        const qsMaxPrice = document.getElementById("qs-max-price");
        const qsAvgDiscount = document.getElementById("qs-avg-discount");

        if (!prices || prices.length === 0) {
            if (qsAvgPrice) qsAvgPrice.textContent = "-";
            if (qsMinPrice) qsMinPrice.textContent = "-";
            if (qsMaxPrice) qsMaxPrice.textContent = "-";
            if (qsAvgDiscount) qsAvgDiscount.textContent = "%0";
            return;
        }

        let totalPrice = 0;
        let minP = Infinity;
        let minModel = "";
        let maxP = -Infinity;
        let maxModel = "";
        let totalDiscountPct = 0;
        let discCount = 0;

        prices.forEach(p => {
            const pVal = priceMode === "list" ? (p.list_price_int || p.price_int) : (p.campaign_price_int || p.price_int);
            totalPrice += pVal;
            if (pVal < minP) {
                minP = pVal;
                minModel = `${p.brand} ${p.model_name}`;
            }
            if (pVal > maxP) {
                maxP = pVal;
                maxModel = `${p.brand} ${p.model_name}`;
            }
            if (p.discount_pct && p.discount_pct > 0) {
                totalDiscountPct += p.discount_pct;
                discCount++;
            }
        });

        const avgP = Math.round(totalPrice / prices.length);
        const avgDisc = discCount > 0 ? (totalDiscountPct / discCount).toFixed(1) : 0;

        if (qsAvgPrice) animateValue(qsAvgPrice, 0, avgP, 500, true);
        if (qsMinPrice) qsMinPrice.textContent = `${formatMoney(minP)} (${minModel})`;
        if (qsMaxPrice) qsMaxPrice.textContent = `${formatMoney(maxP)} (${maxModel})`;
        if (qsAvgDiscount) qsAvgDiscount.textContent = `%${avgDisc} İndirim`;
    }
});
