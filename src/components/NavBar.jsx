import React, { useState, useEffect } from "react";
import { FaBars, FaTimes } from "react-icons/fa";
import { Link } from "react-scroll";

const NavBar = () => {
  const [nav, setNav] = useState(false);
  const [navHeight, setNavHeight] = useState(0);

  useEffect(() => {
    const handleResize = () => {
      const navbar = document.getElementById("navbar");
      setNavHeight(navbar.clientHeight);
    };
    window.addEventListener("resize", handleResize);
    handleResize();
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const links = [
    {
      id: 1,
      link: "home",
    },
    {
      id: 2,
      link: "about",
    },
    {
      id: 3,
      link: "workexperience",
    },
    {
      id: 4,
      link: "projects",
    },
    {
      id: 5,
      link: "experience",
    },
    {
      id: 6,
      link: "education",
    },
    {
      id: 7,
      link: "contact",
    },
  ];

  return (
    <div
      id="navbar"
      className="flex justify-between items-center w-full h-20 px-4 text-white bg-black fixed"
    >
      <div>
        <h1 className="text-5xl font-signature ml-2">Gulshan</h1>
      </div>

      <ul className="hidden md:flex">
        {links.map(({ id,link }) => (
          <li
            key={id}
            className="px-4 cursor-pointer capitalize font-medium text-gray-300 hover:text-gray-100 transition duration-300"
          >
            <Link to={link} smooth duration={500} offset={-navHeight}>
              {link}
            </Link>
          </li>
        ))}
      </ul>

      <div
        onClick={() => setNav(!nav)}
        className="cursor-pointer pr-4 z-10 text-gray-300 md:hidden"
      >
        {nav ? <FaTimes size={30} /> : <FaBars size={30} />}
      </div>

      {nav && (
        <ul className="flex flex-col justify-center items-center absolute top-0 left-0 w-full h-screen bg-gradient-to-b from-black to-gray-800 text-gray-300">
          {links.map(({ id, link }) => (
            <li
              key={id}
              className="px-4 cursor-pointer capitalize py-6 text-4xl hover:text-gray-100 transition duration-300"
            >
              <Link
                onClick={() => setNav(!nav)}
                to={link}
                smooth
                duration={500}
                offset={-navHeight}
              >
                {link}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default NavBar;
