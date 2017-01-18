// Laptop list indexes
var LAPTOP_EMPLOYEE_NAME = 0;
var LAPTOP_MODEL = 2;
var LAPTOP_AGE = 7;
var LAPTOP_MAX_AGE = 2.9;

// Orders list indexes
var ORDER_ENTRY_DATE = 0;
var ORDER_UNDELIVERED_DAYS = 1;
var ORDER_DATE = 2;
var ORDER_DELIVERY_DATE = 3;
var ORDER_FOR_WHOM = 4;
var ORDER_AMOUNT = 5;
var ORDER_DESCRIPTION = 7;
var ORDER_SUPPLIER = 9;
var ORDER_STATUS = 10;
var ORDER_MAX_UNDELIVERED_DAYS = 7;

// Global vars
var SHEET_ID = "*****"
var SEND_TO_EMAIL_ADDR = "*****"
var LAPTOP_LIST_COLUMNS = 8;
var ORDER_LIST_COLUMNS = 11;

function sendOldLaptopsReminderEmail() {
    // 2nd sheet (Laptop List)
    var sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName("Laptop List");
    // First row of data to process
    var startRow = 2;
    // Number of rows to process
    var numRows = sheet.getLastRow();
    // Fetch the range of cells A2:last_one
    var dataRange = sheet.getRange(startRow, 1, numRows, LAPTOP_LIST_COLUMNS);
    // Fetch values table
    var data = dataRange.getValues();
    var htmlArray = "<table border='0'>";
    htmlArray += "<tr><th  align='left'>Name</th>" +
        "<th align='left'>Age</th></tr>";
    for (i in data) {
        var row = data[i];
        var name = row[LAPTOP_EMPLOYEE_NAME];
        var model = row[LAPTOP_MODEL];
        var age = row[LAPTOP_AGE];
        if (age >= LAPTOP_MAX_AGE && name != "SPARE LAPTOP") {
            htmlArray += "<tr>";
            htmlArray += "<td>";
            htmlArray += name;
            htmlArray += "</td>";
            htmlArray += "<td>";
            htmlArray += parseInt(age) + "y " + (age % 1).toFixed(2) * 10
                + "m";
            htmlArray += "</td>";
            htmlArray += "</tr>";
        }
    }
    htmlArray += "</table>";
    var subject = "Monthly laptop replacement script mail ";
    var currentDate = new Date();
    subject += "| month number " + (currentDate.getMonth() + 1);
    MailApp.sendEmail({
        to: SEND_TO_EMAIL_ADDR,
        subject: subject,
        htmlBody: "<p>The following employee's laptops are at or over the" +
        " age of 2.5 years.</p><p>" + htmlArray + "</p>"
    });
}


function sendOrderReminderEmail() {
    // 1st sheet (Orders List)
    var sheet = SpreadsheetApp.openById(SHEET_ID).getSheets()[0];
    // First row of data to process
    var startRow = 2;
    // Number of rows to process
    var numRows = sheet.getLastRow();
    // Fetch the range of cells A2:last_one
    var dataRange = sheet.getRange(startRow, 1, numRows, ORDER_LIST_COLUMNS);
    // Fetch values table
    var data = dataRange.getValues();
    var undeliveredItemsHtmlArray = "<table border='0'>"
        + "<tr>"
        + "<th align='left'>Row</th>"
        + "<th align='left'>Undelivered For (Days)</th>"
        + "<th align='left'>For Whom</th>"
        + "<th align='left'>Amount</th>"
        + "<th align='left'>Description</th>"
        + "<th align='left'>Supplier</th>"
        + "</tr>";
    var deliveredItemsHtmlArray = "<table border='0'>"
        + "<tr>"
        + "<th align='left'>Row</th>"
        + "<th align='left'>Delivery Date</th>"
        + "<th align='left'>For Whom</th>"
        + "<th align='left'>Amount</th>"
        + "<th align='left'>Description</th>"
        + "</tr>";
    var noDeliveryDateHtmlArray = "<table border='0'>"
        + "<tr>"
        + "<th align='left'>Row</th>"
        + "<th align='left'>For Whom</th>"
        + "<th align='left'>Amount</th>"
        + "<th align='left'>Description</th>"
        + "</tr>";
    var awaitingStatusChangeHtmlArray = "<table border='0'>"
        + "<tr>"
        + "<th align='left'>Row</th>"
        + "<th align='left'>For Whom</th>"
        + "<th align='left'>Amount</th>"
        + "<th align='left'>Description</th>"
        + "<th align='left'>Supplier</th>"
        + "<th align='left'>Status</th>"
        + "</tr>";

    for (var i in data) {
        var spreadsheet_row = parseInt(i) + 2;
        var row = data[i];
        var order_entry_date = row[ORDER_ENTRY_DATE];
        var order_undelivered_days = row[ORDER_UNDELIVERED_DAYS];
        var order_for_whom = row[ORDER_FOR_WHOM];
        var order_amount = row[ORDER_AMOUNT];
        var order_description = row[ORDER_DESCRIPTION];
        var order_supplier = row[ORDER_SUPPLIER];
        var order_status = row[ORDER_STATUS];
        var order_delivery_date = row[ORDER_DELIVERY_DATE];

        if (row[ORDER_ENTRY_DATE] != "") {
            if (order_status == "Ordered" &&
                order_undelivered_days >= ORDER_MAX_UNDELIVERED_DAYS) {
                undeliveredItemsHtmlArray += "<tr>";

                undeliveredItemsHtmlArray += "<td>";
                undeliveredItemsHtmlArray += spreadsheet_row;
                undeliveredItemsHtmlArray += "</td>";

                undeliveredItemsHtmlArray += "<td>";
                undeliveredItemsHtmlArray += order_undelivered_days;
                undeliveredItemsHtmlArray += "</td>";

                undeliveredItemsHtmlArray += "<td>";
                undeliveredItemsHtmlArray += order_for_whom;
                undeliveredItemsHtmlArray += "</td>";

                undeliveredItemsHtmlArray += "<td>";
                undeliveredItemsHtmlArray += order_amount;
                undeliveredItemsHtmlArray += "</td>";

                undeliveredItemsHtmlArray += "<td>";
                undeliveredItemsHtmlArray += order_description;
                undeliveredItemsHtmlArray += "</td>";

                undeliveredItemsHtmlArray += "<td>";
                undeliveredItemsHtmlArray += order_supplier;
                undeliveredItemsHtmlArray += "</td>";

                undeliveredItemsHtmlArray += "</tr>";
            } else if (order_status == "Delivered") {
                deliveredItemsHtmlArray += "<tr>";

                deliveredItemsHtmlArray += "<td>";
                deliveredItemsHtmlArray += spreadsheet_row;
                deliveredItemsHtmlArray += "</td>";

                deliveredItemsHtmlArray += "<td>";
                deliveredItemsHtmlArray += order_delivery_date;
                deliveredItemsHtmlArray += "</td>";

                deliveredItemsHtmlArray += "<td>";
                deliveredItemsHtmlArray += order_for_whom;
                deliveredItemsHtmlArray += "</td>";

                deliveredItemsHtmlArray += "<td>";
                deliveredItemsHtmlArray += order_amount;
                deliveredItemsHtmlArray += "</td>";

                deliveredItemsHtmlArray += "<td>";
                deliveredItemsHtmlArray += order_description;
                deliveredItemsHtmlArray += "</td>";

                deliveredItemsHtmlArray += "</tr>";
            } else if (order_status == "Received"
                && row[ORDER_DELIVERY_DATE] == "") {
                noDeliveryDateHtmlArray += "<tr>";

                noDeliveryDateHtmlArray += "<td>";
                noDeliveryDateHtmlArray += spreadsheet_row;
                noDeliveryDateHtmlArray += "</td>";

                noDeliveryDateHtmlArray += "<td>";
                noDeliveryDateHtmlArray += order_for_whom;
                noDeliveryDateHtmlArray += "</td>";

                noDeliveryDateHtmlArray += "<td>";
                noDeliveryDateHtmlArray += order_amount;
                noDeliveryDateHtmlArray += "</td>";

                noDeliveryDateHtmlArray += "<td>";
                noDeliveryDateHtmlArray += order_description;
                noDeliveryDateHtmlArray += "</td>";

                noDeliveryDateHtmlArray += "</tr>";
            } else if (order_status != "Ordered"
                && order_status != "Cancelled" && order_status != "Received") {
                awaitingStatusChangeHtmlArray += "<tr>";

                awaitingStatusChangeHtmlArray += "<td>";
                awaitingStatusChangeHtmlArray += spreadsheet_row;
                awaitingStatusChangeHtmlArray += "</td>";

                awaitingStatusChangeHtmlArray += "<td>";
                awaitingStatusChangeHtmlArray += order_for_whom;
                awaitingStatusChangeHtmlArray += "</td>";

                awaitingStatusChangeHtmlArray += "<td>";
                awaitingStatusChangeHtmlArray += order_amount;
                awaitingStatusChangeHtmlArray += "</td>";

                awaitingStatusChangeHtmlArray += "<td>";
                awaitingStatusChangeHtmlArray += order_description;
                awaitingStatusChangeHtmlArray += "</td>";

                awaitingStatusChangeHtmlArray += "<td>";
                awaitingStatusChangeHtmlArray += order_supplier;
                awaitingStatusChangeHtmlArray += "</td>";


                awaitingStatusChangeHtmlArray += "<td>";
                awaitingStatusChangeHtmlArray += order_status;
                awaitingStatusChangeHtmlArray += "</td>";

                awaitingStatusChangeHtmlArray += "</tr>";
            }
        }
    }

    undeliveredItemsHtmlArray =
        fillEmptyArray({htmlArray: undeliveredItemsHtmlArray});
    deliveredItemsHtmlArray =
        fillEmptyArray({htmlArray: deliveredItemsHtmlArray});
    noDeliveryDateHtmlArray =
        fillEmptyArray({htmlArray: noDeliveryDateHtmlArray});
    awaitingStatusChangeHtmlArray =
        fillEmptyArray({htmlArray: awaitingStatusChangeHtmlArray});

    undeliveredItemsHtmlArray += "</table>";
    deliveredItemsHtmlArray += "</table>";
    noDeliveryDateHtmlArray += "</table>";
    awaitingStatusChangeHtmlArray += "</table>";

    var subject = "Daily order reminder email";
    var currentDate = new Date();
    MailApp.sendEmail({
        to: SEND_TO_EMAIL_ADDR,
        subject: subject,
        htmlBody: "<h2>Undelivered items:</h2>"
        + "<p>" + undeliveredItemsHtmlArray + "</p>"
        + "<h2>Delivered but employee hasn't received yet:</h2>"
        + "<p>" + deliveredItemsHtmlArray + "</p>"
        + "<h2>Awaiting for status change:</h2>"
        + "<p>" + awaitingStatusChangeHtmlArray + "</p>"
        + "<h2>No delivery date:</h2>"
        + "<p>" + noDeliveryDateHtmlArray + "</p>"
    });
}

function fillEmptyArray(parameters) {
    var htmlArray = parameters.htmlArray;

    if (htmlArray.indexOf("<tr>") == -1) {
        htmlArray = "<h3>Empty</h3>"
    }
    return htmlArray;
}
