import {Repo, System} from "./bold_unstable/utils.js";
import * as apps from "./bold_unstable/apps.js";

const repo = new Repo();
repo.addCommonRecipes();

// Add custom recipes below
// Example: repo.addRecipe(apps.hello_sh({ message: "Foo bar!" }).override({ name: "hello_sh2" }));

// Add systems below
repo.addSystem("localhost", new System({
    packages: [
        apps.hello_sh,
        apps.busybox,
    ],
    users: {
        root: {},
        user: {},
    },
}))

console.log(repo.toString());
