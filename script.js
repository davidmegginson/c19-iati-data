
/**
 * Prepopulate the form
 *
 * Use the parameters from the query string, and the values for orgs,
 * sectors, and countries from the JSON data.
 */
function setupForm (data, params) {

    // Check or uncheck a checkbox
    function setCheckbox (id, state) {
        let checkboxNode = document.getElementById(id);
        if (state == "on") {
            checkboxNode.setAttribute("checked", "on");
        } else {
            checkboxNode.removeAttribute("checked");
        }
    }

    // Fill in the options for a select element
    function populateSelect (id, items, defaultValue) {
        let selectNode = document.getElementById(id);
        selectNode.innerHTML = "";
        items = items.sort();
        items.unshift("*");
        items.forEach(item => {
            let optionNode = document.createElement("option");
            optionNode.textContent = item;
            optionNode.setAttribute("name", item);
            if (item == defaultValue) {
                optionNode.setAttribute("selected", "selected");
            }
            selectNode.appendChild(optionNode);
        });
    }

    //
    // Populate the checkboxes
    //
    setCheckbox("form.humanitarian", params.get("humanitarian"));
    setCheckbox("form.strict", params.get("strict"));

    //
    // Populate the select form fields
    //
    populateSelect("form.org", data.getValues("#org+name"), params.get("org"));
    populateSelect("form.sector", data.getValues("#sector"), params.get("sector"));
    populateSelect("form.country", data.getValues("#country"), params.get("country"));
    populateSelect("form.month", data.getValues("#date+month"), params.get("month"));

    // Note: a more-clever version would show only the orgs, sectors,
    // or countries available with the current selections
}


/**
 * Filter the data by org, sector, country, month, humanitarian, and strict
 *
 * This function doesn't actually copy any data; it just constructs a
 * chain of filters that will be applied when it comes time to
 * actually iterate through the data (e.g. for calculating a sum or
 * extracting unique values).
 */
function filterData (data, params) {
    let result = data;
    
    if (params.get("org") && params.get("org") != "*") {
        result = result.withRows({
            pattern: "#org+name",
            test: params.get("org")
        });
    }
    if (params.get("sector") && params.get("sector") != "*") {
        result = result.withRows({
            pattern: "#sector",
            test: params.get("sector")
        });
    }
    if (params.get("country") && params.get("country") != "*") {
        result = result.withRows({
            pattern: "#country",
            test: params.get("country")
        });
    }
    if (params.get("month") && params.get("month") != "*") {
        result = result.withRows({
            pattern: "#date+month",
            test: params.get("month")
        });
    }
    if (params.get("humanitarian") == "on") {
        result = result.withRows({
            pattern: "#indicator+bool+humanitarian",
            test: "1"
        });
    }
    if (params.get("strict") == "on") {
        result = result.withRows({
            pattern: "#indicator+bool+strict",
            test: "1"
        });
    }
    return result;
}


/**
 * Compute totals and update them on the web page
 *
 * This shows how to use the aggregate functions in libhxl-js to
 * compute results. Note that the data is already filtered in the
 * filterData() function, but the filtering is lazy (it doesn't copy
 * the data, but just remembers how to filter it on request).
 */
function showResults(data, params) {

    // Set the content of element#id to a number
    function setResult(id, value) {
        let node = document.getElementById(id);
        node.textContent = value.toLocaleString();
    }

    //
    // update unique-value counts
    //

    // Number of unique orgs
    setResult("org_count", data.getValues("#org+name").length);

    // Number of unique sectors
    setResult("sector_count", data.getValues("#sector").length);

    // Number of unique countries
    setResult("country_count", data.getValues("#country").length);

    // Number of unique activities
    setResult("activity_count", data.getValues("#activity+code").length);

    //
    // update sums
    //

    // create two pre-filtered views, one for commitments and one for spending
    let commitments = data.withRows("x_transaction_type=commitments");
    let spending = data.withRows("x_transaction_type=spending");

    // Net new commitments
    setResult("net_commitments", commitments.getSum("#value+net"));

    // Total commitments
    setResult("total_commitments", commitments.getSum("#value+total"));

    // Net new spending
    setResult("net_spending", spending.getSum("#value+net"));

    // Total spending
    setResult("total_spending", spending.getSum("#value+total"));
}

/**
 * Show the top-10 lists
 */
function showTopLists (data) {

    function populateList (id, data, entityPattern, valuePattern) {
        let listNode = document.getElementById(id);

        // We're already filtered to type "spending". Here's the rest of the pipeline:
        // .count() totals for the tag pattern provided (e.g. #org+name) and number (e.g. #value.net)
        // .sort() by the sums, descending
        // .preview() just the top 10 results
        let rows = spendingData.count(entityPattern, valuePattern).sort("#value+sum", true).preview(10).rows;
        listNode.innerHTML = "";
        rows.forEach(row => {
            let itemNode = document.createElement("li");
            itemNode.textContent = row.get(entityPattern) + " - USD " + row.get("#value+sum").toLocaleString();
            listNode.appendChild(itemNode);
        });
    }

    // First, filter for only spending (we're not counting commitments)
    let spendingData = data.withRows("x_transaction_type=spending");

    // Next, specify what to count for each country
    populateList("top.orgs", spendingData, "#org+name", "#value+total");
    populateList("top.sectors", spendingData, "#sector", "#value+net");
    populateList("top.countries", spendingData, "#country", "#value+net");

}

//
// Main entry point
// First, download transactions.json, then set things moving
//
fetch("data/transactions.json").then(response => {
    response.json().then(rows => {

        // HXLated data
        let data = hxl.wrap(rows);

        // Parameters from the query string
        let params = new URLSearchParams(window.location.search);

        // Filter the data
        let filteredData = filterData(data, params)

        // Populate the form
        setupForm(filteredData, params);

        // Show the results in the HTML page
        showResults(filteredData, params);

        // Show the top 10 lists in the HTML page
        showTopLists(filteredData);
    });
});
