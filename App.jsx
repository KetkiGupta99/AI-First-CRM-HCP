import React from "react";
import { Provider, useDispatch, useSelector } from "react-redux";
import { configureStore, createSlice } from "@reduxjs/toolkit";
import "bootstrap/dist/css/bootstrap.min.css";

/* -------------------- Redux Slice -------------------- */
const interactionSlice = createSlice({
  name: "interaction",
  initialState: {
    hcp_name: "",
    interaction_type: "Meeting",
    date: "",
    time: "",
    attendees: "",
    topics_discussed: "",
    sentiment: "Neutral",
    outcomes: "",
    follow_up_actions: "",
    ai_suggestions_follow_ups: [],
    materials_shared: [],
    samples_distributed: [],
  },
  reducers: {
    fillInteraction: (state, action) => {
      return { ...state, ...action.payload };
    },
  },
});

const { fillInteraction } = interactionSlice.actions;

const store = configureStore({
  reducer: {
    interaction: interactionSlice.reducer,
  },
});

/* -------------------- Interaction Form -------------------- */
const InteractionForm = () => {
  const dispatch = useDispatch();
  const data = useSelector((state) => state.interaction);
  const [chatInput, setChatInput] = React.useState("");
  const [chatMessages, setChatMessages] = React.useState([]);
  const [recommendations, setRecommendations] = React.useState([]);

  // -------- sendPrompt --------
  const sendPrompt = async () => {
    if (!chatInput.trim()) return;

    // Show user message
    setChatMessages((prev) => [...prev, { role: "user", content: chatInput }]);

    try {
      const res = await fetch("http://127.0.0.1:8000/userdata", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          raw_input: chatInput,
          session_id: "session-1",
        }),
      });

      const raw = await res.json();

      // Normalize response
      let data;
      if (typeof raw === "string") {
        try {
          data = JSON.parse(raw);
        } catch {
          data = null;
        }
      } else {
        data = raw;
      }

      // Clarification
      if (data?.clarification_required) {
        setChatMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content:
              data.message +
              "\n\n" +
              data.options.map((o, i) => `${i + 1}. ${o}`).join("\n"),
          },
        ]);
        setChatInput("");
        return;
      }

      // HCP 360
      if (data?.hcp_360_summary) {
        setChatMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.hcp_360_summary },
        ]);
        setChatInput("");
        return;
      }

      //  Meeting Prep Assistant
      if (data?.meeting_prep) {
        setChatMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "🧠 Meeting Preparation\n\n" + data.meeting_prep,
          },
        ]);
        setChatInput("");
        return;
      }

      //  Interaction log / edit
      if (data?.hcp_name) {
        // dispatch(fillInteraction(data));
        dispatch(
          fillInteraction({
            ...data,
            materials_shared: Array.isArray(data.materials_shared)
              ? data.materials_shared
              : [],
            samples_distributed: Array.isArray(data.samples_distributed)
              ? data.samples_distributed
              : [],
          }),
        );

        setChatMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content:
              "✅ Interaction logged successfully!\n\n" +
              "The interaction details have been auto-populated in the form.",
          },
        ]);

        setChatInput("");
        return;
      }

      setChatInput("");
    } catch (err) {
      console.error(err);
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "❌ Error connecting to backend.",
        },
      ]);
    }
  };
  // -------- getNextBestAction --------
  const getNextBestAction = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/next-best-action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          interaction_data: {
            hcp_name: data.hcp_name,
            sentiment: data.sentiment,
            topics_discussed: data.topics_discussed,
            follow_up_actions: data.follow_up_actions,
            product_stage: data.product_stage || "Launch",
            days_since_last_contact: data.days_since_last_contact || 10,
            hcp_preference: data.hcp_preference || "Clinical Data",
          },
        }),
      });

      const result = await res.json();
      setRecommendations(result);
    } catch (err) {
      console.error(err);
      setRecommendations([
        { action: "Error", reason: "Failed to fetch recommendations" },
      ]);
    }
  };
  return (
    <div className="container-fluid p-4 bg-light">
      <h5 className="mb-3 fw-bold">Log HCP Interaction</h5>

      <div className="row g-3">
        {/* ---------------- LEFT PANEL ---------------- */}
        <div className="col-md-8">
          <div className="bg-white border rounded-3 p-3">
            <div className="fw-semibold mb-3 border-bottom pb-2">
              Interaction Details
            </div>

            {/* HCP Name + Interaction Type */}
            <div className="row g-3 mb-2">
              <div className="col-md-6">
                <label className="form-label text-muted small">HCP Name</label>
                <input
                  className="form-control form-control-sm bg-light"
                  value={data.hcp_name || ""}
                  readOnly
                  placeholder="Search or select HCP name..."
                />
              </div>
              <div className="col-md-6">
                <label className="form-label text-muted small">
                  Interaction Type
                </label>
                <select
                  className="form-select form-select-sm bg-light"
                  disabled
                >
                  <option>{data.interaction_type || "Meeting"}</option>
                </select>
              </div>
            </div>

            {/* Date + Time */}
            <div className="row g-3 mb-2">
              <div className="col-md-6">
                <label className="form-label text-muted small">Date</label>
                <div className="input-group input-group-sm">
                  <input
                    type="date"
                    className="form-control bg-light"
                    value={data.date || ""}
                    readOnly
                  />
                  <span className="input-group-text bg-light">📅</span>
                </div>
              </div>
              <div className="col-md-6">
                <label className="form-label text-muted small">Time</label>
                <div className="input-group input-group-sm">
                  <input
                    type="time"
                    className="form-control bg-light"
                    value={data.time || ""}
                    readOnly
                  />
                  <span className="input-group-text bg-light">⏰</span>
                </div>
              </div>
            </div>

            {/* Attendees */}
            <div className="mb-2">
              <label className="form-label text-muted small">Attendees</label>
              <input
                className="form-control form-control-sm bg-light"
                value={data.attendees || ""}
                readOnly
                placeholder="Enter names or search..."
              />
            </div>

            {/* Topics Discussed*/}
            <div className="mb-2">
              <label className="form-label text-muted small">
                Topics Discussed
              </label>
              <div className="position-relative">
                <textarea
                  className="form-control form-control-sm bg-light pe-5"
                  rows="3"
                  value={data.topics_discussed || ""}
                  readOnly
                  placeholder="Enter key dicussion points..."
                />
                {/* Mic Icon */}
                <span
                  className="position-absolute top-50 end-0 translate-middle-y me-2 text-muted"
                  style={{ cursor: "not-allowed" }}
                  title="Voice input (disabled)"
                >
                  🎤
                </span>
              </div>
            </div>
            <small className="text-muted d-flex align-items-center gap-1 mb-3">
              <span>🔄</span>
              <span>Summarized from Voice Note (Requires consent)</span>
            </small>

            <div className="fw-semibold small text-muted mb-2">
              Materials Shared / Samples Distributed
            </div>

            {/* Materials & Samples */}
            <div className="border rounded-2 p-2 mb-2 bg-light">
              <div className="d-flex justify-content-between align-items-center">
                <span className="small fw-semibold">Materials Shared</span>
                <button className="btn btn-outline-secondary btn-sm" disabled>
                  🔍 Search/Add
                </button>
              </div>
              <small className="text-muted">
                {data.materials_shared.length > 0
                  ? data.materials_shared.join(", ")
                  : "No materials added."}
              </small>
            </div>
            <div className="border rounded-2 p-2 mb-3 bg-light">
              <div className="d-flex justify-content-between align-items-center">
                <span className="small fw-semibold">Samples Distributed</span>
                <button className="btn btn-outline-secondary btn-sm" disabled>
                  ➕ Add Sample
                </button>
              </div>
              <small className="text-muted">
                {data.samples_distributed.length > 0
                  ? data.samples_distributed.join(", ")
                  : "No samples added."}
              </small>
            </div>

            {/* Sentiment */}
            <div className="mb-3">
              <label className="form-label text-muted small">
                Observed / Inferred HCP Sentiment
              </label>

              <div className="d-flex gap-5">
                {/* Positive */}
                <div className="form-check text-center">
                  <input
                    className="form-check-input mx-auto"
                    type="radio"
                    name="sentiment"
                    checked={data.sentiment === "Positive"}
                    disabled
                  />
                  <i className="bi bi-emoji-smile fs-4 d-block"></i>
                  <label className="form-check-label fw-bold small">
                    Positive
                  </label>
                </div>

                {/* Neutral */}
                <div className="form-check text-center">
                  <input
                    className="form-check-input mx-auto"
                    type="radio"
                    name="sentiment"
                    checked={data.sentiment === "Neutral"}
                    disabled
                  />
                  <i className="bi bi-emoji-neutral fs-4 d-block"></i>
                  <label className="form-check-label fw-bold small">
                    Neutral
                  </label>
                </div>

                {/* Negative */}
                <div className="form-check text-center">
                  <input
                    className="form-check-input mx-auto"
                    type="radio"
                    name="sentiment"
                    checked={data.sentiment === "Negative"}
                    disabled
                  />
                  <i className="bi bi-emoji-frown fs-4 d-block"></i>
                  <label className="form-check-label fw-bold small">
                    Negative
                  </label>
                </div>
              </div>
            </div>

            {/* Outcomes */}
            <div className="mb-2">
              <label className="form-label text-muted small">Outcomes</label>
              <textarea
                className="form-control form-control-sm bg-light"
                rows="2"
                value={data.outcomes || ""}
                readOnly
                placeholder="Key outcomes or agreements.."
              />
            </div>

            {/* Follow-ups */}
            <div className="mb-3">
              <label className="form-label text-muted small">
                Follow-up Actions
              </label>
              <textarea
                className="form-control form-control-sm bg-light"
                rows="2"
                value={data.follow_up_actions || ""}
                readOnly
                placeholder="Enter next steps or task.."
              />
            </div>
            {/* AI Suggestions */}
            <div className="small">
              <span className="text-muted">AI Suggested Follow-ups:</span>
              <ul className="text-primary mb-0">
                {data.ai_suggestions_follow_ups.length > 0 ? (
                  <ul>
                    {data.ai_suggestions_follow_ups.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <li>No AI Suggestion.</li>
                )}
              </ul>
            </div>
          </div>
        </div>

        {/* ---------------- RIGHT PANEL ---------------- */}
        <div className="col-md-4">
          <div
            className="h-100 d-flex flex-column bg-white border rounded-3"
            style={{ minHeight: "540px" }}
          >
            {/* Header */}
            <div className="p-3 border-bottom">
              <div className="d-flex align-items-center gap-2">
                <span style={{ color: "#0d6efd" }}>🧠</span>
                <strong>AI Assistant</strong>
              </div>
              <small className="text-muted">Log interaction via chat</small>
            </div>

            {/* Right Panel Body */}
            <div className="p-3 flex-grow-1 overflow-auto">
              {/* Helper message */}
              <div
                className="p-3 border rounded-3 mb-2"
                style={{
                  backgroundColor: "#f8f9fa",
                  fontSize: "13px",
                  color: "#444",
                  maxWidth: "95%",
                }}
              >
                <strong>Log interaction details here</strong> (e.g.
                <br />
                “Met Dr. Smith, discussed Product X efficacy, positive
                sentiment, shared brochure”) or ask for help.
              </div>

              {/* Chat Messages */}

              {chatMessages.map((msg, idx) => (
                <div
                  key={idx}
                  style={{
                    fontSize: "13px",
                    color: "#444",
                    whiteSpace: "pre-wrap",
                    marginBottom: "0.5rem",
                  }}
                >
                  <strong>{msg.role === "user" ? "You: " : "AI: "}</strong>
                  {msg.content}
                </div>
              ))}

              {/* ---------------- Tool 4: Next Best Action ---------------- */}
              <div className="mt-4 p-3 border rounded-3">
                <h6 className="fw-bold mb-2">Next Best Action</h6>

                <button
                  className="btn btn-warning w-100 mb-2"
                  onClick={getNextBestAction}
                >
                  Get AI Recommendation
                </button>

                {recommendations.length === 0 && (
                  <small className="text-muted">
                    AI will suggest next steps based on the last interaction,
                    HCP preferences, and compliance rules.
                  </small>
                )}

                {recommendations.length > 0 && (
                  <ul className="list-group mt-2">
                    {recommendations.map((rec, idx) => (
                      <li key={idx} className="list-group-item">
                        <strong>{rec.action}</strong>
                        <br />
                        <small className="text-muted">{rec.reason}</small>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {/* Bottom Input */}
            <div className="p-3 border-top">
              <div className="d-flex gap-2">
                <input
                  className="form-control"
                  placeholder="Describe interaction..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendPrompt()}
                />
                <button className="btn btn-dark px-3" onClick={sendPrompt}>
                  ▲ Log
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/* -------------------- App Wrapper -------------------- */
export default function RootApp() {
  return (
    <Provider store={store}>
      <InteractionForm />
    </Provider>
  );
}
