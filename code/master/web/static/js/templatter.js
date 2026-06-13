"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
// ============================================================================
// ============================================================================
// ============================================================================
var tethys;
(function (tethys) {
    // ============================================================================
    // ============================================================================
    // ============================================================================
    class Templatter {
        // ============================================================================
        /*
        * Initializes the Templatter class.
        *
        * @param templatePath - The path to the template directory on this server.
        */
        constructor(templatePath) {
            this.cyclePosition = 0;
            if (!templatePath.endsWith("/")) {
                templatePath += "/";
            }
            this.templatePath = templatePath;
        }
        // ============================================================================
        getTemplateName() {
            return this.templateName;
        }
        // ============================================================================
        getTemplatePath() {
            return this.templatePath;
        }
        // ============================================================================
        getTemplate(templateName) {
            return __awaiter(this, void 0, void 0, function* () {
                this.templateName = templateName;
                let response = yield fetch(this.templatePath + templateName, {
                    method: 'get'
                });
                this.templateContent = yield response.text();
                return this.templateContent;
            });
        }
        // ============================================================================
        compile(dataObject, nullString = null) {
            let output = this.templateContent;
            let match;
            const regexVars = /\{\{[^}]*\}\}/g;
            const regexLogic = /\{%[^}]*%\}/g;
            // Variables - {{ ... }}
            while ((match = regexVars.exec(this.templateContent)) !== null) {
                const fullMatch = match[0];
                const key = match[0].replace("{{", "").replace("}}", "").trim();
                let keys = key.split(".");
                let lastKey = keys[keys.length - 1];
                if (dataObject[key] !== undefined) {
                    const data = this.ensureGoodData(dataObject[key], nullString);
                    output = output.replace(fullMatch, data);
                }
                else if (dataObject[lastKey] !== undefined) {
                    const data = this.ensureGoodData(dataObject[lastKey], nullString);
                    output = output.replace(fullMatch, data);
                }
            }
            // Logic - {% ... %}
            while ((match = regexLogic.exec(this.templateContent)) !== null) {
                const fullMatch = match[0];
                const matchCore = match[0].replace("{%", "").replace("%}", "").trim();
                output = this.handleLogic(fullMatch, matchCore, output);
            }
            return output;
        }
        // ============================================================================
        ensureGoodData(data, nullString) {
            if (nullString === null) {
                return data;
            }
            if (data === null) {
                return nullString;
            }
            return data;
        }
        // ============================================================================
        handleLogic(fullMatch, matchCore, output) {
            let result = "";
            const partsArray = matchCore.split(" ");
            if (partsArray.length === 0) {
                return output;
            }
            switch (partsArray[0].toLowerCase()) {
                case "cycle":
                    // remove the first item from the array:
                    partsArray.shift();
                    // deal with finding the right opject from the cycle-elements
                    result = this.doCycle(partsArray);
                    break;
                default:
                    result = "";
            }
            return output.replace(fullMatch, result);
        }
        // ============================================================================
        doCycle(partsArray) {
            // length = 3
            // [0], [1], [2]
            if (this.cyclePosition > partsArray.length - 1) {
                this.cyclePosition = 0;
            }
            let result = partsArray[this.cyclePosition];
            result = result.replaceAll("'", "").replaceAll("\"", "");
            this.cyclePosition++;
            return result;
        }
    }
    tethys.Templatter = Templatter;
})(tethys || (tethys = {}));
//# sourceMappingURL=templatter.js.map