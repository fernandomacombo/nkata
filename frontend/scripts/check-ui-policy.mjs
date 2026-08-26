import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(scriptDir, "..");
const repoDir = path.resolve(frontendDir, "..");
const sourceRoots = [
  path.join(frontendDir, "src"),
  path.join(repoDir, "entradas"),
];
const allowedExtensions = new Set([".js", ".jsx", ".ts", ".tsx", ".py", ".html", ".css"]);
const ignoredDirectories = new Set([
  "node_modules",
  "dist",
  "__pycache__",
  "migrations",
  ".git",
]);

// Bloqueia pictogramas usados como emoji na interface sem confundir símbolos
// tipográficos legítimos, como copyright. Inclui o bloco principal de emoji,
// bandeiras e símbolos BMP quando são explicitamente apresentados com VS16.
const emojiPattern = /[\u{1F1E6}-\u{1F1FF}\u{1F300}-\u{1FAFF}]|[\u2600-\u27BF]\uFE0F/gu;

function collectFiles(root, files = []) {
  if (!fs.existsSync(root)) return files;

  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    if (entry.isDirectory() && ignoredDirectories.has(entry.name)) continue;

    const absolute = path.join(root, entry.name);
    if (entry.isDirectory()) {
      collectFiles(absolute, files);
      continue;
    }

    if (allowedExtensions.has(path.extname(entry.name))) files.push(absolute);
  }

  return files;
}

function lineNumberAt(content, index) {
  return content.slice(0, index).split("\n").length;
}

function scanEmojiUsage() {
  const violations = [];

  for (const file of sourceRoots.flatMap((root) => collectFiles(root))) {
    const content = fs.readFileSync(file, "utf8");
    emojiPattern.lastIndex = 0;

    for (const match of content.matchAll(emojiPattern)) {
      violations.push({
        file: path.relative(repoDir, file).replaceAll("\\", "/"),
        line: lineNumberAt(content, match.index),
        symbol: match[0],
      });
    }
  }

  return violations;
}

function checkLucideDependency(errors) {
  const packageJson = JSON.parse(fs.readFileSync(path.join(frontendDir, "package.json"), "utf8"));
  if (!packageJson.dependencies?.["lucide-react"]) {
    errors.push("lucide-react deve permanecer como dependência do frontend.");
  }
}

function checkMobileContract(errors) {
  const mainPath = path.join(frontendDir, "src", "main.jsx");
  const contractPath = path.join(frontendDir, "src", "mobile-app-contract.css");

  if (!fs.existsSync(contractPath)) {
    errors.push("mobile-app-contract.css não existe.");
    return;
  }

  const main = fs.readFileSync(mainPath, "utf8");
  const cssImports = [...main.matchAll(/import\s+["'](.+?\.css)["'];/g)].map((match) => match[1]);
  if (cssImports.at(-1) !== "./mobile-app-contract.css") {
    errors.push("mobile-app-contract.css deve ser o último CSS importado em main.jsx.");
  }

  if (!main.includes("document.body.classList.toggle(\"nk-app-mode\"")) {
    errors.push("main.jsx deve marcar explicitamente o body com nk-app-mode em telas pequenas.");
  }

  const contract = fs.readFileSync(contractPath, "utf8");
  const requiredTokens = [
    "@media (max-width: 820px)",
    "100dvh",
    "safe-area-inset-top",
    "safe-area-inset-bottom",
    "--nk-app-touch: 44px",
    ".nk-bottom-nav",
    "overflow-x: hidden",
    "prefers-reduced-motion",
  ];

  for (const token of requiredTokens) {
    if (!contract.includes(token)) {
      errors.push(`Contrato mobile incompleto: falta "${token}".`);
    }
  }

  if (/(?:^|,)\s*footer\s*(?:,|\{)/m.test(contract)) {
    errors.push(
      "O contrato mobile não pode ocultar <footer> genericamente; use a classe específica do rodapé institucional.",
    );
  }
}

const errors = [];
const emojiViolations = scanEmojiUsage();

if (emojiViolations.length) {
  errors.push(
    "Foram encontrados emojis no código funcional:\n" +
    emojiViolations
      .map((item) => `  - ${item.file}:${item.line} -> ${item.symbol}`)
      .join("\n"),
  );
}

checkLucideDependency(errors);
checkMobileContract(errors);

if (errors.length) {
  console.error("\nNKATA UI policy: FALHOU\n");
  for (const error of errors) console.error(`${error}\n`);
  process.exit(1);
}

console.log("NKATA UI policy: OK");
console.log("- Nenhum emoji funcional encontrado no código verificado.");
console.log("- Lucide React está configurado.");
console.log("- O contrato global de App Mode mobile está ativo.");
