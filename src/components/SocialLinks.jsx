import React, { useState } from "react";
import { FaGithub, FaLinkedin } from "react-icons/fa";
import { HiOutlineMail } from "react-icons/hi";
import { BsFillPersonLinesFill } from "react-icons/bs";

const SocialLinks = () => {
  const [showLinks, setShowLinks] = useState(false);

  const links = [
    {
      id: 1,
      child: (
        <>
          LinkedIn <FaLinkedin size={30} />
        </>
      ),
      href: "https://linkedin.com/in/gulshan-kumar-546462238",
      style: "rounded-tr-md",
    },
    {
      id: 2,
      child: (
        <>
          GitHub <FaGithub size={30} />
        </>
      ),
      href: "https://github.com/GulshanK25",
    },
    {
      id: 3,
      child: (
        <>
          Mail <HiOutlineMail size={30} />
        </>
      ),
      href: "mailto:gulshan.chhablani@gmail.com",
    },
    {
      id: 4,
      child: (
        <>
          Resume <BsFillPersonLinesFill size={30} />
        </>
      ),
      href: "/Gulshan Kumar CV.pdf",
      style: "rounded-br-md",
      // download: true,
    },
  ];

  return (
    <div className="lg:hidden fixed bottom-5 right-5 z-50">
      <button
        className="bg-cyan-950 text-white rounded-full p-3"
        onClick={() => setShowLinks(!showLinks)}
      >
        {showLinks ? "Hide" : "Show"} Links
      </button>
      {showLinks && (
        <ul className="flex flex-col gap-2 bg-cyan-950 p-4 rounded-md">
          {links.map(({ id, child, href, style, download }) => (
            <li key={id}>
              <a
                href={href}
                className="flex items-center text-white"
                download={download}
                target="_blank"
                rel="noreferrer"
              >
                {child}
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default SocialLinks;
