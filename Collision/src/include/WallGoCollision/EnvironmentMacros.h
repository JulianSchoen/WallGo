#ifndef ENVIRONMENTMACROS_H_
#define ENVIRONMENTMACROS_H_

#include "exports_generated.h" // Generated by CMake, shared lib export/import defs

#define WALLGO_API WALLGOCOLLISION_EXPORT

#define WG_STRINGIFY(x) #x

#ifdef _MSC_VER
    #define PRAGMA(x) __pragma(x)
#else
    #define PRAGMA(x) _Pragma(STRINGIFY(x))
#endif

// Stuff that only works for C++20 and newer. For example: std::sin, std::cos were not constexpr until C++20 
#if __cplusplus >= 202002L
	#define WG_CONSTEXPR20 constexpr
#else 
	#define WG_CONSTEXPR20
#endif

#ifdef NDEBUG
    #define WG_DEBUG 0
#else
    // Is debug build
    #define WG_DEBUG 1
#endif

#if WITH_OMP
    #include <omp.h>
#endif

// NB: For MSVC the default OMP version is only 2.X, so some newer features may not be available
#if defined WITH_OMP && _OPENMP >= 200805 // OMP >= 3.0
    #define WG_OMP_SUPPORTS_COLLAPSE 1
#else
    #define WG_OMP_SUPPORTS_COLLAPSE 0
#endif


#if defined WITH_OMP && _MSC_VER
    /* VS implementation of OMP is ****ed and doesn't allow threadprivate on extern variables.
    See https://stackoverflow.com/questions/12560243/using-threadprivate-directive-in-visual-studio */
    #define WG_THREADPRIVATE_EXTERN_VARIABLE(Type, varName) extern __declspec(thread) Type varName

#else
    #define WG_THREADPRIVATE_EXTERN_VARIABLE(Type, varName) \
        extern Type varName; \
        PRAGMA(omp threadprivate(varName))
#endif

#endif // header guard
