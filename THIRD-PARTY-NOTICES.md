# Third-party notices and optional integrations

Content Engine's project-owned material is licensed under [MIT](LICENSE),
Copyright 2026 Workloom Solutions Private Limited. Third-party terms remain separate.

## Optional SEO & GEO skills

Blog and the planning workflows resolve host-installed `seo-*` skills. Their skill
bodies and benchmark implementations are **not bundled in Content Engine**.
They are optional: missing skills leave their formal checks pending; the host may
supply labeled qualitative checks without claiming that a rubric ran.

The referenced integration is Aaron He Zhu's
[SEO & GEO Skills Library](https://github.com/aaron-he-zhu/seo-geo-claude-skills),
licensed under Apache-2.0, Copyright 2024 Aaron He Zhu. The upstream license was
verified at [406239d0bb699fa8cc670e7627e03af561da1eb7](https://github.com/aaron-he-zhu/seo-geo-claude-skills/tree/406239d0bb699fa8cc670e7627e03af561da1eb7).
Its full, unchanged text is included for reference in
[seo-geo-Apache-2.0.txt](third_party/licenses/seo-geo-Apache-2.0.txt).
No upstream NOTICE exists at that recorded snapshot. This is a license-reference
revision, not a claim that all separately installed skills come from that commit.

The Blog workflow names `seo-keyword-research`, `seo-content-refresher`,
`seo-content-quality-auditor` and `seo-geo-content-optimizer`. Planning additionally
names `seo-on-page-seo-auditor`, `seo-internal-linking-optimizer`,
`seo-technical-seo-checker`, `seo-meta-tags-optimizer`,
`seo-schema-markup-generator`, `seo-entity-optimizer`, `seo-competitor-analysis`,
`seo-content-gap-analysis` and `seo-serp-analysis`.

When an importing application supplies these skills, its installed copies retain the
application's `THIRD-PARTY-NOTICES.md`
and their upstream metadata, complete licenses and modification notices. Content
Engine's MIT license does not relicense those copies. Other hosts must preserve
their installed extensions' own attribution and terms. No extension is downloaded
or installed automatically by Content Engine.

## Optional benchmark references

The SEO library's supporting references include MIT material from:

- [CITE domain rating](https://github.com/aaron-he-zhu/cite-domain-rating/tree/2e669c5c801aca6bc8c5f5df3b94ac734f00ff52),
  verified at `2e669c5c801aca6bc8c5f5df3b94ac734f00ff52`.
  Full notice: [CITE-MIT.txt](third_party/licenses/CITE-MIT.txt).
- [CORE-EEAT content benchmark](https://github.com/aaron-he-zhu/core-eeat-content-benchmark/tree/2a04c2f7c0010d6ed2102ff606f6032d4267b0dc),
  verified at `2a04c2f7c0010d6ed2102ff606f6032d4267b0dc`.
  Full notice: [CORE-EEAT-MIT.txt](third_party/licenses/CORE-EEAT-MIT.txt).

Both license texts state Copyright (c) 2026 Aaron. Their full permission notices
are included for reference; the benchmark bodies are not bundled here. An importing
application's adapted benchmark copies must retain those notices alongside Apache terms.

## Optional demo renderer: Pillow

`.github/assets/render-visual-demo.py` imports separately installed
[Pillow](https://github.com/python-pillow/Pillow), whose license is named MIT-CMU in the demo documentation.
Pillow's distribution carries its own [license](https://github.com/python-pillow/Pillow/blob/main/LICENSE).
Pillow code is not vendored in Content Engine, installed by the pipeline importer,
or required by scanner/runtime workflows. Naming its license in demo documentation
can trigger a ScanCode match; that match does not mean Pillow's source was copied.

## Contributor Covenant

CODE_OF_CONDUCT.md is adapted from Contributor Covenant 2.1 under CC BY 4.0;
see the existing [NOTICE](NOTICE) for its source and attribution.
