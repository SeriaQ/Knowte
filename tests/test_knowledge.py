import tempfile
import threading
import unittest
import base64
import sqlite3
from pathlib import Path

from knowte.knowledge import (
    accept_claim_proposal,
    accept_evidence_proposal,
    add_entity_tags_batch,
    canonical_source_key,
    create_annotation,
    create_artifact,
    create_claim,
    create_claim_relation,
    create_claim_proposal,
    create_claim_audit,
    preview_claim_audit,
    next_claim_audit_batch,
    complete_claim_audit_batch,
    get_claim_audit,
    create_evidence,
    create_evidence_proposal,
    create_view,
    create_wiki_proposal,
    delete_view,
    delete_annotation,
    delete_evidence,
    find_related_claims,
    get_source_workspace,
    get_view,
    get_wiki,
    list_artifacts,
    list_claim_proposals,
    list_claims,
    list_evidence,
    list_evidence_proposals,
    list_sources,
    list_views,
    link_evidence_to_claim,
    revise_claim,
    save_source,
    set_entity_tags,
    store_capture,
    update_view,
    accept_wiki_proposal,
    list_wiki_proposals,
    save_project_document,
    list_project_documents,
)


class KnowledgeStoreTests(unittest.TestCase):
    def test_batch_tags_add_without_replacing_existing_evidence_tags(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            source, _, _ = save_source(
                {"title": "Report", "url": "https://example.test/report"},
                path=database,
            )
            workspace = store_capture(source["id"], {
                "url": source["url"], "media_type": "text/html", "sha256": "batch-tags",
                "raw_path": str(Path(temp_dir) / "report.html"),
                "segments": ["First exact quotation. Second exact quotation."],
            }, database)
            segment = workspace["segments"][0]
            first = create_evidence({
                "segment_id": segment["id"], "quote": "First exact quotation.",
                "start_offset": 0, "end_offset": len("First exact quotation."),
            }, database)
            second_start = segment["text"].index("Second")
            second = create_evidence({
                "segment_id": segment["id"], "quote": "Second exact quotation.",
                "start_offset": second_start,
                "end_offset": second_start + len("Second exact quotation."),
            }, database)
            set_entity_tags("evidence", first["id"], ["Existing"], database)
            updated = add_entity_tags_batch(
                "evidence", [first["id"], second["id"]], ["Shared"], database
            )
        self.assertEqual(
            [tag["name"] for tag in updated[first["id"]]], ["Existing", "Shared"]
        )
        self.assertEqual(
            [tag["name"] for tag in updated[second["id"]]], ["Shared"]
        )

    def test_global_wiki_patch_organizes_claims_and_graph_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            first = create_claim(
                {"statement": "Qwen uses grouped-query attention.", "basis": "background", "intentionally_ungrounded": True},
                database,
            )
            second = create_claim(
                {"statement": "Grouped-query attention reduces KV-cache cost.", "basis": "inference", "intentionally_ungrounded": True},
                database,
            )
            create_claim_relation({
                "subject_claim_id": first["id"],
                "object_claim_id": second["id"],
                "relation_type": "supports",
            }, database)
            initial = get_wiki(database)
            self.assertEqual(set(initial["unorganized_claim_ids"]), {first["id"], second["id"]})
            proposal = create_wiki_proposal({
                "summary": "Organize model architecture knowledge.",
                "pages": [
                    {"key": "models", "title": "Models", "parent_key": "", "claim_ids": []},
                    {"key": "qwen", "title": "Qwen", "parent_key": "models", "claim_ids": [first["id"], second["id"]]},
                ],
            }, "wiki-maintainer-v1", "test-model", path=database)
            self.assertEqual(list_wiki_proposals(database)[0]["id"], proposal["id"])
            accepted = accept_wiki_proposal(proposal["id"], database)
            self.assertEqual(accepted["unorganized_claim_ids"], [])
            self.assertEqual(len(accepted["pages"]), 2)
            self.assertEqual(accepted["graph"]["edges"][0]["relation_type"], "supports")
            self.assertEqual(list_wiki_proposals(database), [])

    def test_wiki_proposal_rejects_hierarchy_cycles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            create_claim(
                {"statement": "A Claim.", "basis": "background", "intentionally_ungrounded": True},
                database,
            )
            with self.assertRaisesRegex(ValueError, "cycle"):
                create_wiki_proposal({"pages": [
                    {"key": "a", "title": "A", "parent_key": "b"},
                    {"key": "b", "title": "B", "parent_key": "a"},
                ]}, "wiki-maintainer-v1", path=database)

    def test_temporary_reading_can_be_saved_into_a_project(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            project = create_artifact(
                {"title": "Qwen briefing", "purpose": "Prepare a technical briefing."},
                database,
            )
            document = save_project_document({
                "artifact_id": project["id"],
                "title": "Qwen architecture reading",
                "goal": "Explain the architecture changes.",
                "content": {"sections": [{"heading": "Architecture", "paragraphs": []}]},
            }, database)
            loaded = list_project_documents(project["id"], database)
            self.assertEqual(loaded[0]["id"], document["id"])
            self.assertEqual(loaded[0]["content"]["sections"][0]["heading"], "Architecture")

    def test_evidence_proposal_persists_and_requires_verified_quote(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            source, _, _ = save_source(
                {"title": "Source", "url": "https://example.test"}, path=database
            )
            workspace = store_capture(source["id"], {
                "url": source["url"], "media_type": "text/html", "sha256": "proposal",
                "raw_path": str(Path(temp_dir) / "source.html"),
                "segments": ["Qwen uses grouped query attention for efficient inference."],
                "locators": ["Section 2"],
            }, database)
            segment = workspace["segments"][0]
            proposal = create_evidence_proposal({
                "source_id": source["id"], "segment_id": segment["id"],
                "quote": "Qwen uses grouped query attention for efficient inference.",
                "rationale": "Directly addresses architecture.",
                "caveats": ["The excerpt does not quantify the efficiency gain."],
                "tags": ["Qwen"],
            }, "evidence-proposal-v1", "model", {"focus": "architecture"}, database)
            self.assertEqual(list_evidence_proposals(database)[0]["id"], proposal["id"])
            self.assertEqual(
                proposal["payload"]["caveats"],
                ["The excerpt does not quantify the efficiency gain."],
            )
            accepted = accept_evidence_proposal(proposal["id"], {}, database)
            self.assertEqual(accepted["quote"], proposal["payload"]["quote"])
            self.assertEqual(list_evidence_proposals(database), [])
            with self.assertRaisesRegex(ValueError, "does not match"):
                create_evidence_proposal({
                    "source_id": source["id"], "segment_id": segment["id"],
                    "quote": "Invented quotation.",
                }, "evidence-proposal-v1", path=database)

    def test_legacy_claim_relations_are_removed_instead_of_reinterpreted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            first = create_claim(
                {"statement": "First Claim.", "basis": "background", "intentionally_ungrounded": True},
                database,
            )
            second = create_claim(
                {"statement": "Second Claim.", "basis": "background", "intentionally_ungrounded": True},
                database,
            )
            with sqlite3.connect(database) as connection:
                connection.executescript(
                    """
                    DROP TABLE claim_relations;
                    CREATE TABLE claim_relations (
                        subject_claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
                        object_claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
                        relation_type TEXT NOT NULL CHECK(relation_type IN (
                            'supports', 'contradicts', 'refines'
                        )),
                        rationale TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL,
                        PRIMARY KEY (subject_claim_id, object_claim_id, relation_type),
                        CHECK(subject_claim_id <> object_claim_id)
                    );
                    """
                )
                connection.execute(
                    "INSERT INTO claim_relations VALUES (?, ?, 'refines', '', '2026-01-01T00:00:00Z')",
                    (first["id"], second["id"]),
                )
            list_claims(database)
            with sqlite3.connect(database) as connection:
                rows = connection.execute(
                    "SELECT relation_type FROM claim_relations"
                ).fetchall()
            self.assertEqual(rows, [])

    def test_claim_relations_use_the_reduced_closed_set(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            first = create_claim(
                {"statement": "First Claim.", "basis": "background", "intentionally_ungrounded": True},
                database,
            )
            second = create_claim(
                {"statement": "Second Claim.", "basis": "background", "intentionally_ungrounded": True},
                database,
            )
            relation = create_claim_relation(
                {
                    "subject_claim_id": first["id"],
                    "object_claim_id": second["id"],
                    "relation_type": "related",
                },
                database,
            )
            self.assertEqual(relation["relation_type"], "related")
            with self.assertRaisesRegex(ValueError, "unsupported Claim relation type"):
                create_claim_relation(
                    {
                        "subject_claim_id": first["id"],
                        "object_claim_id": second["id"],
                        "relation_type": "refines",
                    },
                    database,
                )

    def test_view_preserves_ordered_claim_handoff(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            first = create_claim(
                {"statement": "First idea.", "basis": "reported", "intentionally_ungrounded": True},
                database,
            )
            second = create_claim(
                {"statement": "Second idea.", "basis": "inference", "intentionally_ungrounded": True},
                database,
            )
            project = create_artifact(
                {"title": "Qwen research", "purpose": "Understand Qwen architecture."},
                database,
            )

            created = create_view(
                {
                    "title": "Model architecture overview",
                    "view_type": "wiki",
                    "purpose": "Explain the architecture clearly.",
                    "claim_ids": [second["id"], first["id"]],
                    "artifact_id": project["id"],
                },
                database,
            )
            loaded = list_views(database)

            self.assertEqual(created["view_type"], "wiki")
            self.assertEqual(
                [block["block_type"] for block in created["blocks"]],
                ["heading", "claim", "claim"],
            )
            self.assertEqual(created["artifact"]["title"], "Qwen research")
            self.assertEqual(
                [claim["id"] for claim in loaded[0]["claims"]],
                [second["id"], first["id"]],
            )
            updated = update_view(
                created["id"],
                {
                    "title": "Architecture notes",
                    "view_type": "article",
                    "purpose": "A concise technical reading view.",
                    "claim_ids": [first["id"], second["id"]],
                    "blocks": [
                        {"block_type": "heading", "content": "Findings"},
                        {"block_type": "paragraph", "content": "A concise synthesis."},
                        {"block_type": "claim", "claim_id": first["id"]},
                    ],
                },
                database,
            )
            self.assertEqual(updated["title"], "Architecture notes")
            self.assertEqual(updated["view_type"], "article")
            self.assertEqual(
                [claim["id"] for claim in updated["claims"]],
                [first["id"], second["id"]],
            )
            self.assertEqual(updated["blocks"][1]["content"], "A concise synthesis.")
            self.assertEqual(get_view(created["id"], database)["artifact"]["id"], project["id"])
            self.assertTrue(delete_view(created["id"], database))
            self.assertEqual(list_views(database), [])

    def test_claims_preserve_evidence_provenance_and_revision_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            source, _, _ = save_source(
                {"title": "Qwen report", "url": "https://example.test/qwen"},
                path=database,
            )
            workspace = store_capture(
                source["id"],
                {
                    "url": "https://example.test/qwen",
                    "media_type": "text/html",
                    "sha256": "claim-source",
                    "raw_path": str(Path(temp_dir) / "source.html"),
                    "segments": ["Qwen uses grouped-query attention for efficient inference."],
                },
                database,
            )
            evidence = create_evidence(
                {
                    "segment_id": workspace["segments"][0]["id"],
                    "quote": "Qwen uses grouped-query attention",
                    "start_offset": 0,
                    "end_offset": len("Qwen uses grouped-query attention"),
                },
                database,
            )
            claim = create_claim(
                {
                    "statement": "Qwen uses grouped-query attention.",
                    "basis": "reported",
                    "evidence": [{
                        "evidence_id": evidence["id"],
                        "stance": "supports",
                        "rationale": "The report states the mechanism directly.",
                    }],
                    "tags": ["Qwen", "Attention"],
                },
                database,
            )

            revised = revise_claim(
                claim["id"],
                {"statement": "Qwen models use grouped-query attention.", "basis": "reported"},
                database,
            )

            self.assertEqual(len(revised["revisions"]), 2)
            self.assertEqual(revised["evidence"][0]["source_title"], "Qwen report")
            self.assertEqual(revised["evidence"][0]["stance"], "supports")
            self.assertEqual([tag["name"] for tag in revised["tags"]], ["Attention", "Qwen"])
            self.assertEqual(list_evidence(database)[0]["claim_count"], 1)
            self.assertEqual(list_claims(database)[0]["statement"], revised["statement"])

    def test_pending_claim_proposal_survives_reads_until_accept_or_discard(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            proposal = create_claim_proposal(
                {
                    "statement": "A proposed durable Claim.",
                    "basis": "inference",
                    "standing": "unassessed",
                    "evidence": [],
                },
                "claim-proposal-v1",
                "test-model",
                {"kind": "selected_evidence"},
                database,
            )

            self.assertEqual(list_claim_proposals(database)[0]["id"], proposal["id"])
            claim = accept_claim_proposal(
                proposal["id"], {
                    "statement": "An accepted durable Claim.",
                    "intentionally_ungrounded": True,
                }, database
            )

            self.assertEqual(claim["created_via"], "ai_assisted")
            self.assertEqual(claim["statement"], "An accepted durable Claim.")
            self.assertEqual(list_claim_proposals(database), [])

    def test_claim_proposal_accept_rechecks_exact_live_duplicates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            create_claim({
                "statement": "Qwen uses grouped-query attention.",
                "basis": "background", "intentionally_ungrounded": True,
            }, database)
            proposal = create_claim_proposal({
                "statement": "QWEN uses grouped-query attention",
                "basis": "background", "intentionally_ungrounded": True,
            }, "claim-proposal-v3", "test-model", {}, database)

            with self.assertRaisesRegex(ValueError, "equivalent active Claim"):
                accept_claim_proposal(proposal["id"], {}, database)

            self.assertEqual(len(list_claims(database)), 1)
            self.assertEqual(len(list_claim_proposals(database)), 1)

    def test_claim_change_proposals_can_link_evidence_and_create_relations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            source, _, _ = save_source(
                {"title": "Qwen report", "url": "https://example.test/qwen"},
                path=database,
            )
            workspace = store_capture(
                source["id"],
                {
                    "url": source["url"], "media_type": "text/html",
                    "sha256": "claim-change-source",
                    "raw_path": str(Path(temp_dir) / "source.html"),
                    "segments": [
                        "Qwen uses grouped-query attention.",
                        "Independent evaluation confirms grouped-query attention.",
                    ],
                }, database,
            )
            evidence = [
                create_evidence({
                    "segment_id": segment["id"], "quote": segment["text"],
                    "start_offset": 0, "end_offset": len(segment["text"]),
                }, database)
                for segment in workspace["segments"]
            ]
            first = create_claim({
                "statement": "Qwen uses grouped-query attention.",
                "basis": "reported",
                "evidence": [{"evidence_id": evidence[0]["id"], "stance": "supports"}],
                "tags": ["Qwen"],
            }, database)
            second = create_claim({
                "statement": "Grouped-query attention reduces KV-cache costs.",
                "basis": "background", "intentionally_ungrounded": True,
            }, database)

            related = find_related_claims(
                "Qwen grouped-query attention", ["Qwen"], 10, database,
            )
            self.assertEqual(related[0]["claim_id"], first["id"])

            link_proposal = create_claim_proposal({
                "operation": "link_evidence", "target_claim_id": first["id"],
                "target_statement": first["statement"],
                "evidence": [{
                    "evidence_id": evidence[1]["id"], "stance": "supports",
                    "rationale": "Independent confirmation.",
                }],
            }, "claim-proposal-v3", "test-model", {}, database)
            linked = accept_claim_proposal(link_proposal["id"], {}, database)
            self.assertEqual(len(linked["evidence"]), 2)

            relation_proposal = create_claim_proposal({
                "operation": "create_relation",
                "subject_claim_id": first["id"],
                "object_claim_id": second["id"],
                "relation_type": "supports",
                "rationale": "The mechanism supports the efficiency Claim.",
            }, "claim-proposal-v3", "test-model", {}, database)
            relation = accept_claim_proposal(relation_proposal["id"], {}, database)
            self.assertEqual(relation["relation_type"], "supports")
            self.assertEqual(list_claim_proposals(database), [])

    def test_claim_audit_scope_and_progress_persist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            first = create_claim({
                "statement": "Qwen uses grouped-query attention.",
                "basis": "background", "intentionally_ungrounded": True,
                "tags": ["Qwen"],
            }, database)
            second = create_claim({
                "statement": "Qwen models use grouped query attention.",
                "basis": "background", "intentionally_ungrounded": True,
                "tags": ["Qwen"],
            }, database)
            create_claim({
                "statement": "Llama uses a decoder-only architecture.",
                "basis": "background", "intentionally_ungrounded": True,
                "tags": ["Llama"],
            }, database)

            preview = preview_claim_audit({"all_tags": ["Qwen"]}, database)
            self.assertEqual(preview["claim_count"], 2)
            self.assertEqual(preview["candidate_count"], 1)
            audit = create_claim_audit(
                {"all_tags": ["Qwen"]}, "claims-model", database,
            )
            _, batch = next_claim_audit_batch(audit["id"], path=database)
            self.assertEqual(
                {batch[0]["left"]["id"], batch[0]["right"]["id"]},
                {first["id"], second["id"]},
            )
            completed = complete_claim_audit_batch(
                audit["id"], [{
                    "left_claim_id": first["id"],
                    "right_claim_id": second["id"],
                }], 1, model="test-model", path=database,
            )
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(get_claim_audit(audit["id"], database)["proposal_count"], 1)

    def test_audited_claim_merge_preserves_links_tags_and_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            project = create_artifact(
                {"title": "Qwen", "purpose": "Understand Qwen."}, database,
            )
            target = create_claim({
                "statement": "Qwen uses grouped-query attention.",
                "basis": "background", "intentionally_ungrounded": True,
                "artifact_ids": [project["id"]], "tags": ["Qwen"],
            }, database)
            source = create_claim({
                "statement": "Qwen models use grouped query attention.",
                "basis": "background", "intentionally_ungrounded": True,
                "tags": ["Attention"],
            }, database)
            related = create_claim({
                "statement": "Grouped-query attention reduces KV-cache size.",
                "basis": "background", "intentionally_ungrounded": True,
            }, database)
            create_claim_relation({
                "subject_claim_id": source["id"],
                "object_claim_id": related["id"],
                "relation_type": "supports",
            }, database)
            proposal = create_claim_proposal({
                "operation": "merge_claims",
                "target_claim_id": target["id"],
                "source_claim_id": source["id"],
                "merged_statement": "Qwen models use grouped-query attention.",
                "rationale": "The statements have the same identity.",
            }, "claim-audit-v1", "test-model", {}, database)

            merged = accept_claim_proposal(proposal["id"], {}, database)

            self.assertEqual(merged["statement"], "Qwen models use grouped-query attention.")
            self.assertEqual([tag["name"] for tag in merged["tags"]], ["Attention", "Qwen"])
            self.assertEqual(merged["artifacts"][0]["id"], project["id"])
            self.assertEqual(len(merged["revisions"]), 3)
            self.assertTrue(any(
                relation["subject_claim_id"] == target["id"]
                and relation["object_claim_id"] == related["id"]
                for relation in merged["relations"]
            ))
            self.assertEqual(len(list_claims(database)), 2)

    def test_claim_vocabulary_exposes_background_disputed_and_minimal_stances(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            background = create_claim(
                {
                    "statement": "Transformers use attention mechanisms.",
                    "basis": "background",
                    "review_state": "disputed",
                },
                database,
            )
            self.assertEqual(background["basis"], "background")
            self.assertEqual(background["review_state"], "disputed")
            self.assertTrue(background["intentionally_ungrounded"])

            source, _, _ = save_source(
                {"title": "Scoped result", "url": "https://example.test/scoped"},
                path=database,
            )
            workspace = store_capture(
                source["id"],
                {
                    "url": "https://example.test/scoped",
                    "media_type": "text/html",
                    "sha256": "scoped-result",
                    "raw_path": str(Path(temp_dir) / "scoped.html"),
                    "segments": ["The result holds only for short contexts."],
                },
                database,
            )
            evidence = create_evidence(
                {
                    "segment_id": workspace["segments"][0]["id"],
                    "quote": "holds only for short contexts",
                    "start_offset": 11,
                    "end_offset": 40,
                },
                database,
            )
            limited = create_claim(
                {
                    "statement": "The result generalizes across context lengths.",
                    "basis": "inference",
                    "evidence": [{"evidence_id": evidence["id"], "stance": "limits"}],
                },
                database,
            )
            self.assertEqual(limited["evidence"][0]["stance"], "limits")
            self.assertEqual(limited["review_state"], "accepted")

    def test_artifact_requires_title_and_purpose(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            with self.assertRaisesRegex(ValueError, "title is required"):
                create_artifact({"purpose": "Understand a topic."}, database)
            with self.assertRaisesRegex(ValueError, "purpose is required"):
                create_artifact({"title": "Topic"}, database)

    def test_source_is_global_and_artifact_links_are_idempotent(self):
        source_payload = {
            "id": "https://arxiv.org/abs/2401.12345v2",
            "title": "Open model systems",
            "authors": "A. Researcher",
            "year": 2026,
            "abstract": "A useful source.",
            "url": "https://arxiv.org/abs/2401.12345",
            "paper_url": "https://arxiv.org/abs/2401.12345",
            "pdf_url": "https://arxiv.org/pdf/2401.12345",
            "doi_url": "https://doi.org/10.1000/example",
            "source": "arXiv",
            "result_type": "paper",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            artifact = create_artifact(
                {
                    "title": "Open LLM frontier",
                    "purpose": "Understand current open model technology.",
                },
                database,
            )

            first, first_created, first_link = save_source(
                source_payload,
                artifact["id"],
                database,
            )
            second, second_created, second_link = save_source(
                {**source_payload, "title": "Updated title"},
                artifact["id"],
                database,
            )

            self.assertTrue(first_created)
            self.assertTrue(first_link)
            self.assertFalse(second_created)
            self.assertFalse(second_link)
            self.assertEqual(first["id"], second["id"])
            self.assertEqual(second["title"], "Updated title")
            self.assertEqual(len(list_sources(database)), 1)
            self.assertEqual(list_artifacts(database)[0]["source_count"], 1)

    def test_canonical_key_prefers_doi_then_arxiv_then_url(self):
        self.assertEqual(
            canonical_source_key(
                {
                    "doi_url": "https://doi.org/10.1234/ABC",
                    "url": "https://example.test/paper",
                }
            ),
            "doi:10.1234/abc",
        )
        self.assertEqual(
            canonical_source_key(
                {"url": "https://arxiv.org/abs/2501.01234v3"}
            ),
            "arxiv:2501.01234",
        )
        self.assertEqual(
            canonical_source_key(
                {"url": "HTTPS://Example.Test/article/#section"}
            ),
            "url:https://example.test/article",
        )

    def test_first_reads_can_initialize_database_concurrently(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            start = threading.Barrier(3)
            errors = []

            def read_library(reader):
                start.wait()
                try:
                    reader(database)
                except Exception as error:  # pragma: no cover - assertion aid
                    errors.append(error)

            threads = [
                threading.Thread(target=read_library, args=(list_artifacts,)),
                threading.Thread(target=read_library, args=(list_sources,)),
            ]
            for thread in threads:
                thread.start()
            start.wait()
            for thread in threads:
                thread.join()

            self.assertEqual(errors, [])

    def test_capture_evidence_and_annotations_preserve_provenance(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            source, _, _ = save_source(
                {
                    "title": "Qwen report",
                    "url": "https://example.test/qwen",
                    "source": "Web",
                    "result_type": "web",
                },
                path=database,
            )
            text = "Qwen uses a mixture of techniques for efficient inference."
            workspace = store_capture(
                source["id"],
                {
                    "url": "https://example.test/qwen",
                    "media_type": "text/html",
                    "sha256": "abc",
                    "raw_path": str(Path(temp_dir) / "abc.html"),
                    "segments": [text],
                },
                database,
            )
            segment = workspace["segments"][0]
            quote = "mixture of techniques"
            start = text.index(quote)
            evidence = create_evidence(
                {
                    "segment_id": segment["id"],
                    "quote": quote,
                    "start_offset": start,
                    "end_offset": start + len(quote),
                },
                database,
            )
            source_note = create_annotation(
                {
                    "target_type": "source",
                    "target_id": source["id"],
                    "body": "Read the evaluation section.",
                },
                database,
            )
            evidence_note = create_annotation(
                {
                    "target_type": "evidence",
                    "target_id": evidence["id"],
                    "body": "Potential support for the inference-efficiency Claim.",
                },
                database,
            )
            loaded = get_source_workspace(source["id"], database)

            self.assertEqual(loaded["source"]["capture_state"], "captured")
            self.assertEqual(loaded["evidence"][0]["quote"], quote)
            self.assertEqual(loaded["annotations"][0]["id"], source_note["id"])
            self.assertEqual(
                loaded["evidence"][0]["annotations"][0]["id"],
                evidence_note["id"],
            )
            tags = set_entity_tags(
                "evidence", evidence["id"], ["Architecture", "Qwen"], database
            )
            self.assertEqual([tag["name"] for tag in tags], ["Architecture", "Qwen"])
            loaded = get_source_workspace(source["id"], database)
            self.assertEqual(len(loaded["evidence"][0]["tags"]), 2)
            with self.assertRaisesRegex(ValueError, "unsupported tag entity type"):
                set_entity_tags(
                    "annotation", evidence_note["id"], ["Needs review"], database
                )
            self.assertTrue(delete_annotation(evidence_note["id"], database))
            self.assertTrue(delete_evidence(evidence["id"], database))
            loaded = get_source_workspace(source["id"], database)
            self.assertEqual(loaded["evidence"], [])

    def test_evidence_rejects_a_quote_not_in_the_capture(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            source, _, _ = save_source(
                {"title": "Source", "url": "https://example.test"},
                path=database,
            )
            workspace = store_capture(
                source["id"],
                {
                    "url": "https://example.test",
                    "media_type": "text/html",
                    "sha256": "def",
                    "raw_path": str(Path(temp_dir) / "def.html"),
                    "segments": ["Captured text is immutable."],
                },
                database,
            )
            with self.assertRaisesRegex(ValueError, "does not match"):
                create_evidence(
                    {
                        "segment_id": workspace["segments"][0]["id"],
                        "quote": "Invented",
                        "start_offset": 0,
                        "end_offset": 8,
                    },
                    database,
                )

    def test_evidence_accepts_pdf_text_normalization_differences(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            source, _, _ = save_source(
                {"title": "PDF Source", "url": "https://example.test/paper.pdf"},
                path=database,
            )
            workspace = store_capture(
                source["id"],
                {
                    "url": "https://example.test/paper.pdf",
                    "media_type": "application/pdf",
                    "sha256": "pdf-normalization",
                    "raw_path": str(Path(temp_dir) / "paper.pdf"),
                    "segments": ["A multi-\ncolumn PDF uses efficient ﬂow matching."],
                },
                database,
            )
            evidence = create_evidence(
                {
                    "segment_id": workspace["segments"][0]["id"],
                    "quote": "A multicolumn PDF uses efficient flow matching.",
                    "locator": "Page 1",
                },
                database,
            )
            self.assertEqual(evidence["locator"], "Page 1")

    def test_snapshot_evidence_keeps_region_and_image_provenance(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "knowte.db"
            source, _, _ = save_source(
                {"title": "Visual Source", "url": "https://example.test/visual"},
                path=database,
            )
            workspace = store_capture(
                source["id"],
                {
                    "url": "https://example.test/visual.pdf",
                    "media_type": "application/pdf",
                    "sha256": "visual-capture",
                    "raw_path": str(Path(temp_dir) / "content" / "visual.pdf"),
                    "segments": ["Page with a chart."],
                    "locators": ["Page 1"],
                },
                database,
            )
            png = (
                b"\x89PNG\r\n\x1a\n"
                b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            )
            evidence = create_evidence(
                {
                    "evidence_type": "snapshot",
                    "segment_id": workspace["segments"][0]["id"],
                    "locator": "Page 1",
                    "anchor": {
                        "page": 1,
                        "region": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4},
                    },
                    "image_data": (
                        "data:image/png;base64,"
                        + base64.b64encode(png).decode("ascii")
                    ),
                },
                database,
            )
            loaded = get_source_workspace(source["id"], database)

            self.assertEqual(evidence["evidence_type"], "snapshot")
            self.assertTrue(loaded["evidence"][0]["has_snapshot"])
            self.assertEqual(
                loaded["evidence"][0]["anchor"]["region"]["width"],
                0.3,
            )


if __name__ == "__main__":
    unittest.main()
