import * as os from "os";
import * as std from "std";
import * as apps from "./apps.js";

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
    constructor(common_recipes = true) {
        this.named_recipes = {};
        this.recipes = {};
        this.named_systems = {};
        this.systems = {};

        if (common_recipes) {
            this.addCommonRecipes();
        }
    }

    addRecipe(recipe, unique_name = false) {
        if (typeof recipe === "function") {
            recipe = recipe({});
        }
        this.recipes[`${recipe.metadata.name}@${recipe.hash()}`] = recipe.metadata;
        Object.values(recipe.subrecipes).forEach((subrecipe) => {
            this.addRecipe(subrecipe);
        });
        if (unique_name) {
            if (this.named_recipes.hasOwnProperty(recipe.metadata.name)) {
                throw "Duplicate recipe name marked as 'unique_name'";
            }
            this.named_recipes[recipe.metadata.name] = recipe.hash();
        }
    }

    addSystem(system, unique_name = true) {
        if (typeof system === "function") {
            system = system({});
        }

        // Add all recipes not already added to the repo
        system.metadata.packages = system.metadata.packages.map((recipe) => {
            if (typeof recipe === "function") {
                recipe = recipe({});
            }
            this.addRecipe(recipe);
            return `${recipe.metadata.name}@${recipe.hash()}`;
        });

        this.systems[`${system.metadata.name}@${system.hash()}`] = system.metadata;
        if (unique_name) {
            if (this.named_systems.hasOwnProperty(system.metadata.name)) {
                throw "Duplicate system name marked as 'unique_name' (hint: pass 'false' as the second argument to addSystem)";
            }
            this.named_systems[system.metadata.name] = system.hash();
        }
    }

    toString() {
        return sortedJsonStringify({
            named_recipes: this.named_recipes,
            recipes: this.recipes,
            named_systems: this.named_systems,
            systems: this.systems,
        });
    }

    addCommonRecipes() {
        this.addRecipe(apps.hello_sh, true);
        this.addRecipe(apps.busybox, true);
        this.addRecipe(apps.libexample, true);
        this.addRecipe(apps.libexample_bin, true);
    }
}

export class Recipe {
    constructor(metadata) {
        this.metadata = metadata;
        this.subrecipes = {};
        metadata.depends = metadata.depends || {};
        metadata.recipe.buildDepends = metadata.recipe.buildDepends || {};

        metadata.depends = Object.fromEntries(Object.entries(metadata.depends).map(([dep_name, dep]) => {
            if (typeof dep === "string") {
                return [dep_name, dep];
            }
            if (typeof dep === "function") {
                dep = dep({});
            }
            let dep_id = `${dep.metadata.name}@${dep.hash()}`;
            this.subrecipes[dep_id] = dep;
            return [dep_name, dep_id];
        }));

        metadata.recipe.buildDepends = Object.fromEntries(Object.entries(metadata.recipe.buildDepends).map(([dep_name, dep]) => {
            if (typeof dep === "string") {
                return [dep_name, dep];
            }
            if (typeof dep === "function") {
                dep = dep({});
            }
            let dep_id = `${dep.metadata.name}@${dep.hash()}`;
            this.subrecipes[dep_id] = dep;
            return [dep_name, dep_id];
        }));

        this.recipe = metadata.recipe;
    }

    hash() {
        return run_cmd(['./bold_unstable/hashRecipe.sh'], sortedJsonStringify(this.metadata)).trim();
    }

    override(updates) {
        return new Recipe(deep_merge(updates, deep_merge(this.metadata, {})));
    }

    modify(callback) {
        return new Recipe(callback(deep_merge(this.metadata, {})));
    }
}

export class System {
    constructor(metadata) {
        this.metadata = metadata;
    }

    hash() {
        return run_cmd(['./bold_unstable/hashRecipe.sh'], sortedJsonStringify(this.metadata)).trim();
    }

    override(updates) {
        return new System(deep_merge(updates, deep_merge(this.metadata, {})));
    }

    modify(callback) {
        return new System(callback(deep_merge(this.metadata, {})));
    }
}

export function cLibrary(name) {
    return `-Wl,-rpath -Wl,"$DEP_${name}"/lib -isystem "$EXT_${name}" -L"$BDEP_${name}"/lib -l:${name}.so`;
}