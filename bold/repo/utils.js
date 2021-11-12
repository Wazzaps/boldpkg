import * as os from "os";
import * as std from "std";

// Seems to work
// Source: https://stackoverflow.com/a/53593328
function sortedJsonStringify(obj) {
    let allKeys = [];
    let seen = {};
    JSON.stringify(obj, function (key, value) {
        if (!(key in seen)) {
            allKeys.push(key);
            seen[key] = null;
        }
        return value;
    });
    allKeys.sort();
    return JSON.stringify(obj, allKeys);
}

// XXX: Will deadlock on long inputs
function run_cmd(cmd, input) {
    let [in_read_fd, in_write_fd] = os.pipe();
    let [out_read_fd, out_write_fd] = os.pipe();
    let proc = os.exec(cmd, {
        block: false,
        stdin: in_read_fd,
        stdout: out_write_fd,
    });
    os.close(in_read_fd);
    os.close(out_write_fd);

    let process_input = std.fdopen(in_write_fd, "w");
    process_input.puts(input);
    process_input.flush();
    process_input.close();

    let process_output = std.fdopen(out_read_fd, "r");
    let output = process_output.readAsString();
    process_output.close();

    os.waitpid(proc);

    return output;
}

// Source: https://gist.github.com/ahtcx/0cd94e62691f539160b32ecda18af3d6#gistcomment-3889214
function deep_merge(source, target) {
    for (const [key, val] of Object.entries(source)) {
        if (val !== null && typeof val === `object`) {
            if (target[key] === undefined) {
                target[key] = new val.__proto__.constructor();
            }
            deep_merge(val, target[key]);
        } else {
            target[key] = val;
        }
    }
    return target; // we're replacing in-situ, so this is more for chaining than anything else
}

export class Repo {
    constructor() {
        this.recipes = {};
    }

    addRecipe(recipe) {
        if (typeof recipe === "function") {
            recipe = recipe({});
        }
        this.recipes[`${recipe.metadata.name}@${recipe.hash()}`] = recipe.metadata;
    }

    toString() {
        return sortedJsonStringify({
            recipes: this.recipes,
        });
    }
}

export class Recipe {
    constructor(metadata) {
        this.metadata = metadata;
        this.recipe = metadata.recipe;
    }

    hash() {
        return run_cmd(['./hashRecipe.sh'], sortedJsonStringify(this.metadata)).trim();
    }

    override(updates) {
        return new Recipe(deep_merge(updates, deep_merge(this.metadata, {})));
    }
}
