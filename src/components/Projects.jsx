import React, { useState } from "react";
import mindmed from "../assets/mindmed.png";
import portfolio from "../assets/portfolio.jpg";
import studentConnect from "../assets/sm.jpeg";
import softhouse from "../assets/softhouse_logo.jpeg";
import smarthouse from "../assets/smarthouse.jpg";

// Original, local vector artwork. No remote image hosting is required.
import reviewCover from "../assets/project-covers/ai-code-review.svg";
import ragCover from "../assets/project-covers/website-rag.svg";
import permittoCover from "../assets/project-covers/permitto.svg";
import homeAssistantCover from "../assets/project-covers/home-assistant.svg";
import { projectCategories, projects } from "../data/portfolioData";

const projectImages = {
  review: reviewCover,
  rag: ragCover,
  permitto: permittoCover,
  ha: homeAssistantCover,
  mindmed,
  portfolio,
  student: studentConnect,
  softhouse,
  smarthouse,
};

// Older beginner projects are intentionally hidden from the portfolio,
// without deleting their repositories or requiring edits to your data file.
const displayProjects = projects.filter(
  (project) =>
    !["pig", "timer"].includes(project.id) &&
    !/^(pig game|timer)$/i.test(project.name.trim())
);

const featuredProjects = displayProjects.filter((project) => project.featured);
const additionalProjects = displayProjects.filter((project) => !project.featured);

const categoryFilters = [["all", "All Categories"], ...Object.entries(projectCategories)];

const ProjectCard = ({ project }) => {
  const cover = projectImages[project.image];

  return (
    <article className="group flex h-full flex-col overflow-hidden rounded-lg border border-gray-600 bg-gray-900/30 shadow-md transition-all duration-500 hover:-translate-y-1 hover:scale-[1.02] hover:border-cyan-600 hover:shadow-lg hover:shadow-cyan-700/40">
      <div className="relative h-44 overflow-hidden bg-slate-900 sm:h-48">
        {cover ? (
          <img
            src={cover}
            alt=""
            className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-110"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-cyan-950 p-6">
            <span aria-hidden="true" className="text-center text-2xl font-bold text-cyan-200">
              {project.name}
            </span>
          </div>
        )}
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/20 to-transparent opacity-40 transition-opacity duration-300 group-hover:opacity-10" />
      </div>
      <div className="flex flex-1 flex-col p-5">
        <p className="mb-2 text-xs uppercase tracking-wider text-cyan-300">
          {project.category}
        </p>
        <h3 className="mb-2 text-xl font-semibold leading-snug text-white">
          {project.name}
        </h3>
        <p className="mb-4 flex-1 text-sm leading-relaxed text-gray-300">
          {project.description}
        </p>
        <div className="mb-4 flex flex-wrap gap-2">
          {project.tech.map((tech) => (
            <span
              key={tech}
              className="rounded border border-gray-600 bg-gray-800 px-2 py-1 text-xs text-gray-200"
            >
              {tech}
            </span>
          ))}
        </div>
        <div className="flex flex-wrap gap-4">
          {project.githubLink && (
            <a
              href={project.githubLink}
              aria-label={"View source on GitHub for " + project.name}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-cyan-300 transition-colors hover:text-cyan-100 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300"
            >
              View Source
            </a>
          )}
          {project.liveLink && (
            <a
              href={project.liveLink}
              aria-label={"Visit live site for " + project.name}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-cyan-300 transition-colors hover:text-cyan-100 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300"
            >
              Visit Live Site
            </a>
          )}
        </div>
      </div>
    </article>
  );
};

const Projects = () => {
  const [showAll, setShowAll] = useState(false);
  const [category, setCategory] = useState("all");
  const isFiltered = category !== "all";
  const visibleProjects = isFiltered
    ? [...featuredProjects, ...additionalProjects].filter((project) =>
        project.filterCategories?.includes(category)
      )
    : featuredProjects;

  return (
    <section id="projects" className="scroll-mt-20 bg-gradient-to-b from-gray-800 to-black py-12 text-white">
      <div className="container mx-auto max-w-screen-xl px-4">
        <h2 className="mb-8 border-b-4 border-gray-500 pb-4 text-4xl font-bold">
          Featured Projects
        </h2>
        <div role="group" aria-label="Filter by project category" className="mb-8 flex flex-wrap gap-2">
          {categoryFilters.map(([value, label]) => (
            <button
              key={value}
              type="button"
              aria-pressed={category === value}
              onClick={() => setCategory(value)}
              className={
                "rounded-md border px-3 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-300 " +
                (category === value
                  ? "border-cyan-500 bg-cyan-900 text-white"
                  : "border-gray-600 text-gray-200 hover:border-cyan-400 hover:bg-cyan-900/40")
              }
            >
              {label}
            </button>
          ))}
        </div>
        <p role="status" className="sr-only">
          {isFiltered
            ? projectCategories[category] + ": " + visibleProjects.length + " projects"
            : showAll
              ? "Showing all projects"
              : "Showing featured projects"}
        </p>
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-2">
          {visibleProjects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
        {isFiltered && visibleProjects.length === 0 && (
          <p className="text-gray-300">No projects in this category yet.</p>
        )}
        {!isFiltered && additionalProjects.length > 0 && (
          <>
            <div className="mt-10 flex justify-center">
              <button
                type="button"
                aria-expanded={showAll}
                aria-controls="additional-projects"
                onClick={() => setShowAll((value) => !value)}
                className="rounded-md border border-cyan-500 px-6 py-3 text-cyan-100 transition-colors duration-300 hover:bg-cyan-900/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300"
              >
                {showAll ? "Hide More Projects" : "Show More Projects"}
              </button>
            </div>
            <div id="additional-projects" hidden={!showAll}>
              <div className="mt-8 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
                {additionalProjects.map((project) => (
                  <ProjectCard key={project.id} project={project} />
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </section>
  );
};

export default Projects;
