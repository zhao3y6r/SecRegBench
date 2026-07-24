import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

const SEARCH_ENDPOINT = "https://www.csrc.gov.cn/getSearch";
const PAGE_SIZE = 20;
const RETRIEVED_AT = new Date().toISOString();

const CHANNELS = [
  {
    id: "2f087f7010fb43788a9015f21448447a",
    key: "hunan_administrative_supervisory_measures",
    name: "CSRC Hunan Regulatory Bureau: Administrative Supervisory Measures",
    landingPage:
      "https://www.csrc.gov.cn/hunan/c104484/zfxxgk_zdgk.shtml",
    queries: [
      "\u6295\u8d44\u987e\u95ee",
      "\u9002\u5f53\u6027",
      "\u5ba2\u6237\u6295\u8bc9",
      "\u6295\u8bc9\u5904\u7406",
      "\u627f\u8bfa\u6536\u76ca",
      "\u53d8\u76f8\u627f\u8bfa",
      "\u865a\u5047\u5ba3\u4f20",
      "\u8bef\u5bfc\u6027",
      "\u6295\u8d44\u5efa\u8bae",
      "\u5ba2\u6237\u56de\u8bbf",
      "\u4e1a\u52a1\u63a8\u5e7f",
      "\u8425\u9500",
      "\u65e0\u8d44\u8d28",
      "\u98ce\u9669\u63ed\u793a",
      "\u5ba2\u6237\u670d\u52a1",
      "\u4ece\u4e1a\u8d44\u683c",
      "\u516c\u4f17\u5a92\u4f53",
      "\u76f4\u64ad",
      "\u5fae\u4fe1",
      "\u8350\u80a1",
      "\u8bc1\u5238\u63a8\u8350",
      "\u4ea7\u54c1\u63a8\u8350",
      "\u4e2a\u4eba\u4fe1\u606f",
      "\u5ba2\u6237\u4fe1\u606f",
      "\u4fe1\u606f\u6cc4\u9732",
      "\u4ea4\u6613\u6743\u9650",
      "\u77e5\u8bc6\u6d4b\u8bc4\u7b54\u6848",
      "\u7559\u75d5",
      "\u5408\u89c4\u5ba1\u6838",
      "\u5185\u5e55\u4fe1\u606f",
      "\u5229\u76ca\u51b2\u7a81",
    ],
  },
  {
    id: "8d1c236a98924e38a854bbb9f215efb9",
    key: "csrc_central_administrative_punishments",
    name: "China Securities Regulatory Commission: Administrative Punishments",
    landingPage:
      "https://www.csrc.gov.cn/csrc/c101928/zfxxgk_zdgk.shtml",
    queries: [
      "\u8bc1\u5238\u6295\u8d44\u54a8\u8be2",
      "\u6295\u8d44\u5efa\u8bae",
      "\u9002\u5f53\u6027",
      "\u627f\u8bfa\u6536\u76ca",
      "\u865a\u5047\u5ba3\u4f20",
      "\u5ba2\u6237\u6295\u8bc9",
      "\u5185\u5e55\u4ea4\u6613",
      "\u64cd\u7eb5\u5e02\u573a",
    ],
  },
];

const CATEGORY_PATTERNS = {
  unqualified_or_scoped_advice: [
    "\u6295\u8d44\u987e\u95ee",
    "\u6295\u8d44\u5efa\u8bae",
    "\u8350\u80a1",
    "\u8bc1\u5238\u63a8\u8350",
    "\u65e0\u8d44\u8d28",
    "\u4ece\u4e1a\u8d44\u683c",
    "\u8bc1\u5238\u6295\u8d44\u54a8\u8be2",
  ],
  suitability_and_access: [
    "\u9002\u5f53\u6027",
    "\u98ce\u9669\u627f\u53d7",
    "\u98ce\u9669\u7b49\u7ea7",
    "\u98ce\u9669\u63ed\u793a",
    "\u98ce\u9669\u6d4b\u8bc4",
    "\u4ea4\u6613\u6743\u9650",
    "\u77e5\u8bc6\u6d4b\u8bc4",
  ],
  misleading_or_guaranteed_marketing: [
    "\u627f\u8bfa\u6536\u76ca",
    "\u53d8\u76f8\u627f\u8bfa",
    "\u4fdd\u672c\u4fdd\u606f",
    "\u865a\u5047\u5ba3\u4f20",
    "\u8bef\u5bfc\u6027",
    "\u5938\u5927\u5ba3\u4f20",
    "\u4e1a\u52a1\u63a8\u5e7f",
    "\u8425\u9500",
  ],
  complaint_workflow: [
    "\u5ba2\u6237\u6295\u8bc9",
    "\u6295\u8bc9\u5904\u7406",
    "\u5ba2\u6237\u7ea0\u7eb7",
    "\u6295\u8bc9\u7ea0\u7eb7",
  ],
  public_or_social_channel: [
    "\u516c\u4f17\u5a92\u4f53",
    "\u76f4\u64ad",
    "\u5fae\u4fe1",
    "\u81ea\u5a92\u4f53",
    "\u516c\u4f17\u53f7",
  ],
  recordkeeping_and_review: [
    "\u7559\u75d5",
    "\u5ba2\u6237\u56de\u8bbf",
    "\u5408\u89c4\u5ba1\u6838",
    "\u5185\u90e8\u63a7\u5236",
  ],
  privacy_or_customer_information: [
    "\u4e2a\u4eba\u4fe1\u606f",
    "\u5ba2\u6237\u4fe1\u606f",
    "\u4fe1\u606f\u6cc4\u9732",
    "\u4fe1\u606f\u4fdd\u62a4",
  ],
  inside_information: [
    "\u5185\u5e55\u4fe1\u606f",
    "\u5185\u5e55\u4ea4\u6613",
  ],
  market_manipulation: [
    "\u5e02\u573a\u64cd\u7eb5",
    "\u64cd\u7eb5\u5e02\u573a",
  ],
  conflict_of_interest: ["\u5229\u76ca\u51b2\u7a81"],
};

const RULE_TO_EXTERNAL_CATEGORIES = {
  "RULE-CN-EDUCATION-ANSWER": ["official_investor_question_proxy"],
  "RULE-CN-GUARANTEE-REFUSE": ["misleading_or_guaranteed_marketing"],
  "RULE-CN-INSIDE-INFO-REFUSE": ["inside_information"],
  "RULE-CN-MANIPULATION-REFUSE": ["market_manipulation"],
  "RULE-CN-PUBLIC-SPECIFIC-ADVICE-REFUSE": [
    "unqualified_or_scoped_advice",
    "public_or_social_channel",
  ],
  "RULE-CN-DIRECT-AI-PERSONALIZED-ESCALATE": [
    "unqualified_or_scoped_advice",
    "public_or_social_channel",
  ],
  "RULE-CN-ADVICE-ASSESSMENT-GATE": [
    "unqualified_or_scoped_advice",
    "suitability_and_access",
  ],
  "RULE-CN-PROACTIVE-UNSUITABLE-REFUSE": [
    "suitability_and_access",
    "misleading_or_guaranteed_marketing",
  ],
  "RULE-CN-LOWEST-RISK-UNMATCHED-REFUSE": ["suitability_and_access"],
  "RULE-CN-INVESTOR-INITIATED-MISMATCH-ESCALATE": [
    "suitability_and_access",
  ],
  "RULE-CN-ACCESS-FAIL-REFUSE": ["suitability_and_access"],
  "RULE-CN-COMPLAINT-ROUTE": ["complaint_workflow"],
};

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

function stripTags(value) {
  return String(value ?? "")
    .replace(/<[^>]*>/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

async function fetchJson(channel, query, page) {
  const body = new URLSearchParams({
    type: "content",
    searchContent: query,
    channelId: channel.id,
    isAgg: "true",
    isIdentifier: "true",
    page: String(page),
    size: String(PAGE_SIZE),
  });
  let lastError;
  for (let attempt = 1; attempt <= 4; attempt += 1) {
    try {
      const response = await fetch(SEARCH_ENDPOINT, {
        method: "POST",
        headers: {
          accept: "application/json, text/javascript, */*; q=0.01",
          "content-type": "application/x-www-form-urlencoded",
          referer: channel.landingPage,
          "user-agent": "Mozilla/5.0 SecRegBench academic audit",
          "x-requested-with": "XMLHttpRequest",
        },
        body,
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, 300 * attempt));
    }
  }
  throw lastError;
}

async function fetchQuery(channel, query) {
  const first = await fetchJson(channel, query, 1);
  const total = Number(first?.data?.total ?? 0);
  const results = [...(first?.data?.results ?? [])];
  const pages = Math.ceil(total / PAGE_SIZE);
  for (let start = 2; start <= pages; start += 6) {
    const batch = [];
    for (let page = start; page < Math.min(start + 6, pages + 1); page += 1) {
      batch.push(fetchJson(channel, query, page));
    }
    const responses = await Promise.all(batch);
    for (const response of responses) {
      results.push(...(response?.data?.results ?? []));
    }
  }
  return { total, results };
}

function classify(text) {
  const categories = [];
  const evidenceTerms = {};
  for (const [category, patterns] of Object.entries(CATEGORY_PATTERNS)) {
    const hits = patterns.filter((pattern) => text.includes(pattern));
    if (hits.length) {
      categories.push(category);
      evidenceTerms[category] = hits;
    }
  }
  return { categories, evidenceTerms };
}

async function loadScenarioCoverage(corpusPath, categoryCounts) {
  const text = await readFile(corpusPath, "utf8");
  const ruleCounts = new Map();
  let scenarioCount = 0;
  let scenarioWithRegulatoryRecordCategory = 0;
  let scenarioWithAnyPublicAnchor = 0;
  for (const line of text.split(/\r?\n/)) {
    if (!line.trim()) continue;
    const row = JSON.parse(line);
    scenarioCount += 1;
    const ruleIds = row?.label?.controlling_rule_ids ?? [];
    let hasRegulatoryRecordCategory = false;
    let hasAnyPublicAnchor = false;
    for (const ruleId of ruleIds) {
      ruleCounts.set(ruleId, (ruleCounts.get(ruleId) ?? 0) + 1);
      for (const category of RULE_TO_EXTERNAL_CATEGORIES[ruleId] ?? []) {
        if (category === "official_investor_question_proxy") {
          hasAnyPublicAnchor = true;
        } else if ((categoryCounts[category] ?? 0) > 0) {
          hasRegulatoryRecordCategory = true;
          hasAnyPublicAnchor = true;
        }
      }
    }
    if (hasRegulatoryRecordCategory) scenarioWithRegulatoryRecordCategory += 1;
    if (hasAnyPublicAnchor) scenarioWithAnyPublicAnchor += 1;
  }
  const ruleCoverage = {};
  for (const [ruleId, scenarioSupport] of [...ruleCounts.entries()].sort()) {
    const categories = RULE_TO_EXTERNAL_CATEGORIES[ruleId] ?? [];
    const recordCategories = categories.filter(
      (category) =>
        category !== "official_investor_question_proxy" &&
        (categoryCounts[category] ?? 0) > 0,
    );
    ruleCoverage[ruleId] = {
      scenario_support: scenarioSupport,
      external_categories: categories,
      regulatory_record_categories_present: recordCategories,
      covered_by_regulatory_records: recordCategories.length > 0,
      covered_by_combined_public_anchors:
        recordCategories.length > 0 ||
        categories.includes("official_investor_question_proxy"),
    };
  }
  return {
    scenario_count: scenarioCount,
    scenarios_with_regulatory_record_category:
      scenarioWithRegulatoryRecordCategory,
    scenarios_with_any_public_anchor: scenarioWithAnyPublicAnchor,
    rule_coverage: ruleCoverage,
  };
}

async function main() {
  const root = process.cwd();
  const artifactRoot = path.join(root, "artifact");
  const outputDir = path.join(
    artifactRoot,
    "audits",
    "external_regulatory_cases",
  );
  const corpusPath = path.join(
    artifactRoot,
    "data",
    "secregbench_public_v014.jsonl",
  );
  const proxyReportPath = path.join(
    outputDir,
    "external_style_proxy_report_v013.json",
  );

  const records = new Map();
  const queryTotals = {};
  for (const channel of CHANNELS) {
    queryTotals[channel.key] = {};
    for (const query of channel.queries) {
      const { total, results } = await fetchQuery(channel, query);
      queryTotals[channel.key][query] = total;
      for (const source of results) {
        const url = String(source.url ?? "").startsWith("//")
          ? `https:${source.url}`
          : String(source.url ?? "");
        const key = `${channel.key}:${source.manuscriptId ?? source.mId ?? url}`;
        const content = stripTags(source.content ?? source.contentHtml);
        const existing = records.get(key) ?? {
          record_id: sha256(url || key).slice(0, 20),
          source_channel: channel.key,
          source_channel_name: channel.name,
          title: stripTags(source.title ?? source.subTitle),
          url,
          published_date: String(
            source.publishedTimeStr ?? source.publishedTimeForDate ?? "",
          ).slice(0, 10),
          content_sha256: sha256(content),
          query_terms: new Set(),
          categories: [],
          category_evidence_terms: {},
        };
        existing.query_terms.add(query);
        const { categories, evidenceTerms } = classify(
          `${existing.title}\n${content}`,
        );
        existing.categories = [...new Set([...existing.categories, ...categories])];
        for (const [category, terms] of Object.entries(evidenceTerms)) {
          existing.category_evidence_terms[category] = [
            ...new Set([
              ...(existing.category_evidence_terms[category] ?? []),
              ...terms,
            ]),
          ];
        }
        records.set(key, existing);
      }
    }
  }

  const registry = [...records.values()]
    .map((record) => ({
      ...record,
      query_terms: [...record.query_terms].sort(),
      categories: [...record.categories].sort(),
      category_evidence_terms: Object.fromEntries(
        Object.entries(record.category_evidence_terms)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([category, terms]) => [category, [...terms].sort()]),
      ),
    }))
    .filter((record) => record.categories.length > 0)
    .sort(
      (a, b) =>
        b.published_date.localeCompare(a.published_date) ||
        a.url.localeCompare(b.url),
    );

  const categoryCounts = {};
  const channelCounts = {};
  for (const record of registry) {
    channelCounts[record.source_channel] =
      (channelCounts[record.source_channel] ?? 0) + 1;
    for (const category of record.categories) {
      categoryCounts[category] = (categoryCounts[category] ?? 0) + 1;
    }
  }

  const proxyReport = JSON.parse(await readFile(proxyReportPath, "utf8"));
  const officialQuestionCount =
    proxyReport.official_candidates_without_automatic_flags;
  const scenarioCoverage = await loadScenarioCoverage(
    corpusPath,
    categoryCounts,
  );

  await mkdir(outputDir, { recursive: true });
  const registryText = `${registry
    .map((record) => JSON.stringify(record))
    .join("\n")}\n`;
  const registryPath = path.join(
    outputDir,
    "official_regulatory_records_v017.jsonl",
  );
  await writeFile(registryPath, registryText, "utf8");

  const dates = registry
    .map((record) => record.published_date)
    .filter(Boolean)
    .sort();
  const report = {
    schema_version: "0.1.0",
    status:
      "PASS_PUBLIC_REGULATORY_RECORD_CATEGORY_ALIGNMENT_NOT_REAL_DIALOGUE_VALIDATION",
    retrieved_at: RETRIEVED_AT,
    official_search_endpoint: SEARCH_ENDPOINT,
    channels: CHANNELS.map(({ id, key, name, landingPage, queries }) => ({
      id,
      key,
      name,
      landing_page: landingPage,
      fixed_queries: queries,
    })),
    query_totals_before_deduplication: queryTotals,
    regulatory_records_after_deduplication_and_category_filter: registry.length,
    regulatory_records_by_channel: channelCounts,
    regulatory_records_by_category: categoryCounts,
    regulatory_record_date_range: {
      earliest: dates.at(0) ?? null,
      latest: dates.at(-1) ?? null,
    },
    official_investor_question_proxy_items: officialQuestionCount,
    combined_public_external_anchor_items:
      registry.length + officialQuestionCount,
    scenario_category_anchor_coverage: scenarioCoverage,
    hashes: {
      registry_sha256: sha256(registryText),
      corpus_sha256: sha256(await readFile(corpusPath)),
      external_style_proxy_report_sha256: sha256(
        await readFile(proxyReportPath),
      ),
    },
    claim_boundary: {
      permitted:
        "The synthetic benchmark is grounded in registered public rules and its rule categories are externally aligned with a deterministically retrieved pool of official supervisory/punishment records; a separate official-question proxy measures surface-language distance.",
      not_permitted: [
        "The 10,000 synthetic scenarios are 10,000 real punishment cases.",
        "The official records are customer-service conversation logs.",
        "Category alignment establishes production-traffic representativeness.",
        "Keyword retrieval or category alignment supplies item-level gold actions.",
      ],
      raw_official_content_redistributed: false,
      registry_contains: [
        "official title",
        "official URL",
        "publication date",
        "content hash",
        "fixed query terms",
        "deterministic category tags and evidence terms",
      ],
    },
  };
  const reportPath = path.join(
    outputDir,
    "official_regulatory_case_audit_report_v017.json",
  );
  await writeFile(
    reportPath,
    `${JSON.stringify(report, null, 2)}\n`,
    "utf8",
  );

  console.log(
    JSON.stringify(
      {
        registry_path: registryPath,
        report_path: reportPath,
        regulatory_records: registry.length,
        official_question_items: officialQuestionCount,
        combined_public_external_anchors:
          registry.length + officialQuestionCount,
        category_counts: categoryCounts,
        scenario_category_anchor_coverage: scenarioCoverage,
      },
      null,
      2,
    ),
  );
}

await main();
