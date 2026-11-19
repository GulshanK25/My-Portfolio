import React from "react";
import "./skillset.css";
import {
  SiNextdotjs,
  SiTypescript,
  SiExpress,
  SiFastapi,
  SiDocker,
  SiGit,
  SiPytorch,
  SiTensorflow,
  SiScikitlearn,
  SiApachespark,
  SiApachehadoop,
} from "react-icons/si";
import { FaCode, FaFlask } from "react-icons/fa";

// Keep your existing image logos, glowing shadows, and hover behavior.
import html from "../assets/html.png";
import css from "../assets/css.png";
import javascript from "../assets/javascript.png";
import reactImage from "../assets/react.png";
import node from "../assets/node.png";
import graphql from "../assets/graphql.png";
import github from "../assets/github.png";
import tailwind from "../assets/tailwind.png";
import python from "../assets/Python.jpg";
import java from "../assets/Java.png";
import mongodb from "../assets/Mongodb.png";
import mysql from "../assets/mysqllogo.png";
import angular from "../assets/Angular.png";
import postgress from "../assets/postgress.png";
import kotlin from "../assets/Koltin.jpg";
import jetpack from "../assets/jetpack compose.png";

// Custom artwork for concepts/tools without a suitable icon in react-icons.
import langgraph from "../assets/skill-icons/langgraph.svg";
import rag from "../assets/skill-icons/rag.svg";
import ollama from "../assets/skill-icons/ollama.svg";
import chromadb from "../assets/skill-icons/chromadb.svg";
import sentenceTransformers from "../assets/skill-icons/sentence-transformers.svg";
import restApis from "../assets/skill-icons/rest-apis.svg";
import { extraSkills } from "../data/portfolioData";

const existingSkills = [
  ["HTML", html, "shadow-orange-500"],
  ["CSS", css, "shadow-blue-500"],
  ["JavaScript", javascript, "shadow-yellow-500"],
  ["React", reactImage, "shadow-blue-600"],
  ["Tailwind CSS", tailwind, "shadow-sky-400"],
  ["Kotlin", kotlin, "shadow-purple-400"],
  ["Node.js", node, "shadow-green-300"],
  ["GraphQL", graphql, "shadow-pink-400"],
  ["GitHub", github, "shadow-gray-400"],
  ["Python", python, "shadow-cyan-800"],
  ["Java", java, "shadow-gray-700"],
  ["MongoDB", mongodb, "shadow-green-400"],
  ["MySQL", mysql, "shadow-blue-400"],
  ["Angular", angular, "shadow-red-400"],
  ["PostgreSQL", postgress, "shadow-blue-400"],
  ["Jetpack Compose", jetpack, "shadow-blue-200"],
];

// Icon components from the existing react-icons dependency are local SVGs.
// These styles deliberately mirror the original colorful skill cards.
const addedSkillVisuals = {
  LangGraph: { image: langgraph, color: "#4ade80" },
  RAG: { image: rag, color: "#22d3ee" },
  Ollama: { image: ollama, color: "#c4b5fd" },
  ChromaDB: { image: chromadb, color: "#fb7185" },
  "Sentence Transformers": { image: sentenceTransformers, color: "#60a5fa" },
  PyTorch: { Icon: SiPytorch, color: "#ee4c2c" },
  TensorFlow: { Icon: SiTensorflow, color: "#ff9700" },
  "scikit-learn": { Icon: SiScikitlearn, color: "#f7931e" },
  "Next.js": { Icon: SiNextdotjs, color: "#f8fafc" },
  TypeScript: { Icon: SiTypescript, color: "#3178c6" },
  Express: { Icon: SiExpress, color: "#d1d5db" },
  FastAPI: { Icon: SiFastapi, color: "#00a393" },
  "REST APIs": { image: restApis, color: "#38bdf8" },
  Docker: { Icon: SiDocker, color: "#2496ed" },
  Git: { Icon: SiGit, color: "#f05032" },
  "Apache Spark": { Icon: SiApachespark, color: "#e25a1c" },
  Hadoop: { Icon: SiApachehadoop, color: "#f2c94c" },
  pytest: { Icon: FaFlask, color: "#73c071" },
};

const BaseSkillCard = ({ name, children, color = "#22d3ee" }) => (
  <div
    className="portfolio-skill-card group flex min-h-[162px] flex-col items-center justify-center rounded-lg border p-3 text-center"
    style={{ "--skill-accent": color }}
  >
    <div className="mb-3 flex h-20 w-20 items-center justify-center transition-transform duration-300 group-hover:scale-110">
      {children}
    </div>
    <p className="text-sm font-medium text-white md:text-base">{name}</p>
  </div>
);

const AdditionalSkillCard = ({ name }) => {
  const visual = addedSkillVisuals[name] || { Icon: FaCode, color: "#67e8f9" };
  const Icon = visual.Icon;
  return (
    <BaseSkillCard name={name} color={visual.color}>
      {visual.image ? (
        <img src={visual.image} alt="" className="h-[68px] w-[68px] object-contain" loading="lazy" />
      ) : (
        <Icon aria-hidden="true" className="h-[62px] w-[62px]" style={{ color: visual.color }} />
      )}
    </BaseSkillCard>
  );
};

const existingSkillAccent = {
  "shadow-orange-500": "#f97316",
  "shadow-blue-500": "#3b82f6",
  "shadow-yellow-500": "#eab308",
  "shadow-blue-600": "#2563eb",
  "shadow-sky-400": "#38bdf8",
  "shadow-purple-400": "#c084fc",
  "shadow-green-300": "#86efac",
  "shadow-pink-400": "#f472b6",
  "shadow-gray-400": "#9ca3af",
  "shadow-cyan-800": "#0891b2",
  "shadow-gray-700": "#94a3b8",
  "shadow-green-400": "#4ade80",
  "shadow-blue-400": "#60a5fa",
  "shadow-red-400": "#f87171",
  "shadow-blue-200": "#bfdbfe",
};

const SectionTitle = ({ children, detail }) => (
  <div className="mb-6">
    <h3 className="border-l-4 border-cyan-400 pl-4 text-xl font-semibold text-cyan-200 md:text-2xl">
      {children}
    </h3>
    {detail && <p className="mt-2 pl-5 text-sm text-slate-300">{detail}</p>}
  </div>
);

const SkillsGrid = ({ children }) => (
  <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 md:grid-cols-4 lg:gap-7">
    {children}
  </div>
);

const Skillset = () => {
  const aiSkills = extraSkills.find(({ category }) => category === "AI & ML");
  const otherGroups = extraSkills.filter(({ category }) => category !== "AI & ML");

  return (
    <section id="skillset" className="portfolio-skills-section py-14 text-white">
      <div className="container mx-auto max-w-screen-xl px-4">
        <h2 className="mb-10 border-b-4 border-slate-500 pb-4 text-4xl font-bold">
          Technical Skills
        </h2>

        {/* Lead with applied AI: keep the exact illustrated skill-card format. */}
        {aiSkills && (
          <div>
            <SectionTitle detail="Technologies I use to build AI assistants, retrieval pipelines and ML applications.">
              AI & Machine Learning
            </SectionTitle>
            <SkillsGrid>
              {aiSkills.items.map((name) => (
                <AdditionalSkillCard key={name} name={name} />
              ))}
            </SkillsGrid>
          </div>
        )}

        {/* The original logos remain. They now share the same responsive glow as new cards. */}
        <div className="mt-16">
          <SectionTitle detail="Languages, frameworks and databases used across my software projects.">
            Core Development
          </SectionTitle>
          <SkillsGrid>
            {existingSkills.map(([name, src, shadowClass]) => (
              <BaseSkillCard
                key={name}
                name={name}
                color={existingSkillAccent[shadowClass] || "#22d3ee"}
              >
                <img
                  src={src}
                  alt=""
                  className="h-20 w-20 object-contain"
                  loading="lazy"
                />
              </BaseSkillCard>
            ))}
          </SkillsGrid>
        </div>

        {otherGroups.map((group) => (
          <div key={group.category} className="mt-16">
            <SectionTitle>{group.category}</SectionTitle>
            <SkillsGrid>
              {group.items.map((name) => (
                <AdditionalSkillCard key={name} name={name} />
              ))}
            </SkillsGrid>
          </div>
        ))}
      </div>
    </section>
  );
};

export default Skillset;
