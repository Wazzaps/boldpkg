import * as apps from "./apps/apps.js";
import {Repo} from "./utils.js";

const repo = new Repo();

// Add recipes here
repo.addRecipe(apps.hello_sh);
repo.addRecipe(apps.busybox);

console.log(repo.toString());
