# WARD Live: Chrome Web Store listing

Fill the fields in the developer dashboard from the sections below. The same text works for Edge Add-ons. Replace SERVER_ADDRESS with the hosted server address before submitting, and set the same address as the default in extension/popup.js before zipping.

## Store listing

**Name**
WARD Live

**Summary** (132 characters maximum; this one is 120)
Audit the page you are on against WCAG 2.1 and 2.2 and see where it stands among 135,604 audited civil society websites.

**Category**
Accessibility

**Language**
English

**Description**

WARD Live checks the accessibility of the web page you are looking at and tells you three things most checkers leave out: how the page compares with thousands of similar sites, what changes when the standard moves from WCAG 2.1 to WCAG 2.2, and what someone without technical training could fix.

Click the icon on any page and WARD Live will

- evaluate the page under WCAG 2.1 AA and WCAG 2.2 AA from a single fetch, side by side, and explain what the move to 2.2 changes for this page
- place the result in the distribution of 135,604 civil society homepages audited in the United Kingdom, Australia, the United States, New Zealand and Ireland, telling you what share of them had fewer and what share had more violations
- list each violated criterion with a plain-language explanation of what was detected, who it affects and how to fix it, with a link to the W3C guidance
- outline the offending elements on the page itself so you can see where the problems are
- open the full report, which turns the violations into remediation tasks split between content editors and developers, with acceptance criteria and a CSV download

WARD Live uses WARD, the open-source checker behind a published five-country census of civil society websites. The rules are the same ones used for the census, so every number you see is on the same scale as the published dataset.

WARD is a static checker. It reads the page as served and does not run scripts, so it reports a floor: colour contrast and anything that needs a rendered page are outside its scope. A clean result means the page passes the machine-checkable rules, not the whole standard.

WARD Live is free, open source and carries no advertising or analytics. It is developed at the Institute for Data and AI Research, University of Galway, Ireland. The extension sends only the address of the current page to the WARD Live server, which fetches the page itself and returns the result. By default it uses the public server at SERVER_ADDRESS; you can point it at your own server in Settings.

Code and data: https://github.com/sohaibayub/ward-live
Census dataset: https://doi.org/10.5281/zenodo.23529469

**Website**
https://github.com/sohaibayub/ward-live

**Support URL**
https://github.com/sohaibayub/ward-live/issues

**Privacy policy**
https://sohaibayub.github.io/ward-live/privacy-policy.html

## Privacy practices tab

**Single purpose description**
WARD Live audits the accessibility of the web page in the active tab against WCAG 2.1 and 2.2, compares the result with a published census of civil society websites, and shows where the violations are on the page.

**Permission justifications**

activeTab
Needed to read the address of the page the user is looking at when they click the extension button, and to draw outlines on that page when they ask for them. Nothing happens until the button is clicked.

tabs
Needed to read the address of the current web page so it can be sent to the audit server. The extension does not read or track other tabs.

scripting
Needed to add temporary outlines and labels to the offending elements on the current page when the user clicks "Outline on page", and to remove them when the user clicks "Clear". No code is loaded from a remote source.

storage
Needed to remember two settings chosen by the user: the address of the audit server and the country used for the census comparison.

Host permissions
None requested.

Remote code
No. All code ships inside the extension package. The extension makes an HTTPS request to the audit server and displays the JSON it returns.

**Data usage disclosures**

Which data does the extension collect?
Website content: the URL of the current page is sent to the audit server when the user clicks "Audit this page". No other category applies. No personally identifiable information, health, financial, authentication, personal communications, location, web history or user activity data is collected.

Certifications (tick all three)
- I do not sell or transfer user data to third parties, outside of the approved use cases.
- I do not use or transfer user data for purposes that are unrelated to my item's single purpose.
- I do not use or transfer user data to determine creditworthiness or for lending purposes.

## Graphics to prepare

- Icon 128 x 128: extension/icons/icon128.png (already in the package)
- Screenshots, 1280 x 800 or 640 x 400, at least one, up to five. Suggested set: the popup after an audit; the page with outlines drawn; the full report's version cards and census chart; the remediation backlog.
- Small promo tile 440 x 280 (optional): the icon and the name on the teal background.

## Edge Add-ons

Same package, same text. Edge asks for the privacy policy URL and a short "notes for certification" field; paste the single purpose description there and add that the extension requires a running WARD Live server at SERVER_ADDRESS.

## Before zipping for the store

1. Set the hosted address as the default in extension/popup.js (the DEFAULT constant) and in this listing.
2. Zip the contents of the extension folder (manifest.json at the top level of the zip, not inside a folder).
3. Load the zip unpacked once more and run one audit to confirm the hosted server answers over HTTPS.
