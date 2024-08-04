

// ============================================================================
// ============================================================================
// ============================================================================
namespace tethys {

    // ============================================================================
    // ============================================================================
    // ============================================================================
    export class Templatter {

        private templatePath: string;
        private templateName: string;
        private templateContent: string;


        private cyclePosition = 0;


        // ============================================================================
        /*
        * Initializes the Templatter class.
        *
        * @param templatePath - The path to the template directory on this server.
        */
        constructor(templatePath: string) {

            if (!templatePath.endsWith("/")) {
                templatePath += "/";
            }

            this.templatePath = templatePath;
        }


        // ============================================================================
        public getTemplateName(): string {
            return this.templateName;
        }

        // ============================================================================
        public getTemplatePath(): string {
            return this.templatePath;
        }


        // ============================================================================

        public async getTemplate(templateName: string): Promise<string> {
            this.templateName = templateName;

            let response = await fetch(
                this.templatePath + templateName,
                {
                    method: 'get'
                });

            this.templateContent = await response.text();
            return this.templateContent;
        }


        // ============================================================================
        public compile(
            dataObject,
            nullString = null): string {

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
        private ensureGoodData(data, nullString) {

            if (nullString === null) {
                return data;
            }

            if (data === null) {
                return nullString;
            }

            return data;
        }


        // ============================================================================
        private handleLogic(
            fullMatch,
            matchCore,
            output): string {

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
        private doCycle(partsArray) {

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
}